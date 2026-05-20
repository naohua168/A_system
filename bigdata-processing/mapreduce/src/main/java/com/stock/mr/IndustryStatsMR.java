/**
 * IndustryStatsMR — 行业统计 MapReduce 作业（优化版）
 *
 * 输入: HDFS 上的日K线 CSV (stock_code,date,open,high,low,close,volume,amount,change_pct,turnover)
 *
 * 处理流程:
 *   Mapper: 解析CSV → (stock_code, [change_pct, volume])
 *   Reducer: 通过分布式缓存或回退映射表获取行业信息 → 聚合 → 行业统计结果
 *
 * 输出: HDFS /user/hadoop/stock_data/analysis/industry_stats/
 *       industry    avg_change_pct    up_count    down_count    total_volume
 *
 * ���行:
 *   # 使用分布式缓存（推荐，需先准备 industry_mapping.csv）
 *   hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       com.stock.mr.IndustryStatsMR \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/industry_stats/ \
 *       -files hdfs:///user/hadoop/stock_data/basic/industry_mapping.csv
 *
 *   # 或使用硬编码回退（本地测试/开发环境）
 *   hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       com.stock.mr.IndustryStatsMR \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/industry_stats/
 *
 * industry_mapping.csv 格式（无表头）:
 *   000001,银行
 *   600519,白酒
 *   300750,新能源
 *   ...
 */
package com.stock.mr;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.net.URI;
import java.util.HashMap;
import java.util.Map;

public class IndustryStatsMR {

    private static final Logger LOG = LoggerFactory.getLogger(IndustryStatsMR.class);

    // ============================================================
    // 股票 → 行业 回退映射表（开发/测试环境使用）
    // ============================================================
    private static final Map<String, String> FALLBACK_INDUSTRY_MAP = new HashMap<>();

    static {
        FALLBACK_INDUSTRY_MAP.put("000001", "银行");
        FALLBACK_INDUSTRY_MAP.put("600519", "白酒");
        FALLBACK_INDUSTRY_MAP.put("300750", "新能源");
        FALLBACK_INDUSTRY_MAP.put("000858", "白酒");
        FALLBACK_INDUSTRY_MAP.put("600036", "银行");
        FALLBACK_INDUSTRY_MAP.put("601318", "保险");
        FALLBACK_INDUSTRY_MAP.put("002415", "通信");
        FALLBACK_INDUSTRY_MAP.put("300059", "互联网金融");
        FALLBACK_INDUSTRY_MAP.put("002463", "半导体");
        FALLBACK_INDUSTRY_MAP.put("688017", "高端装备");
    }

    // ============================================================
    // Mapper: 解析 CSV → (stock_code, "DATA#change_pct#volume#date")
    // ============================================================
    public static class IndustryStatsMapper
            extends Mapper<Object, Text, Text, Text> {

        private Text outKey = new Text();
        private Text outValue = new Text();

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {

            String line = value.toString().trim();
            if (line.startsWith("trade_date") || line.startsWith("date") || line.isEmpty()) {
                return;
            }

            String[] fields = line.split(",");
            if (fields.length < 6) return;

            try {
                String stockCode;
                String changePct;
                String volume;
                String date;

                String firstField = fields[0].trim();
                if (firstField.matches(".*[A-Za-z].*")) {
                    // Format A: stock_code,date,open,high,low,close,volume,amount,change_pct
                    stockCode = firstField;
                    date = fields[1].trim();
                    changePct = fields.length > 8 ? fields[8].trim() : "0";
                    volume = fields[6].trim();
                } else {
                    // Format B: date,open,high,low,close,volume,amount,...,stock_code
                    stockCode = fields[fields.length - 1].trim();
                    date = firstField;
                    changePct = fields.length > 8 ? fields[8].trim() : "0";
                    volume = fields[5].trim();
                }

                outKey.set(stockCode);
                outValue.set("DATA#" + changePct + "#" + volume + "#" + date);
                context.write(outKey, outValue);

            } catch (Exception e) {
                context.getCounter("IndustryStatsMR", "SKIPPED_LINES").increment(1);
            }
        }
    }

    // ============================================================
    // Reducer: 通过行业映射聚合统计
    // ============================================================
    public static class IndustryStatsReducer
            extends Reducer<Text, Text, Text, Text> {

        /** 行业映射表：优先从分布式缓存加载，失败则使用回退映射 */
        private Map<String, String> industryMap;

        @Override
        protected void setup(Context context) throws IOException {
            industryMap = new HashMap<>();

            // 尝试从分布式缓存加载完整行业映射
            URI[] cacheFiles = context.getCacheFiles();
            boolean loadedFromCache = false;

            if (cacheFiles != null && cacheFiles.length > 0) {
                for (URI uri : cacheFiles) {
                    String fileName = uri.getPath();
                    if (fileName != null && fileName.endsWith("industry_mapping.csv")) {
                        LOG.info("从分布式缓存加载行业映射: {}", uri);
                        String localPath = "./industry_mapping.csv";
                        loadedFromCache = loadFromFile(localPath);
                        if (loadedFromCache) break;
                    }
                }
            }

            // 同时加载备用的 Symlink 路径
            if (!loadedFromCache) {
                try {
                    loadedFromCache = loadFromFile("industry_mapping.csv");
                } catch (Exception ignored) {}
            }

            if (loadedFromCache) {
                LOG.info("行业映射加载成功: 共 {} 条记录", industryMap.size());
            } else {
                // 回退到硬编码映射表
                industryMap.putAll(FALLBACK_INDUSTRY_MAP);
                LOG.warn("分布式缓存不可用，使用硬编码回退映射表 (共 {} 条)", industryMap.size());
                context.getCounter("IndustryStatsMR", "FALLBACK_MAP_USED").increment(1);
            }
        }

        /**
         * 从本地文件加载行业映射 CSV
         * 格式: stock_code,industry （无表头）
         */
        private boolean loadFromFile(String filePath) {
            try (BufferedReader reader = new BufferedReader(new FileReader(filePath))) {
                String line;
                int count = 0;
                while ((line = reader.readLine()) != null) {
                    line = line.trim();
                    if (line.isEmpty() || line.startsWith("#") || line.startsWith("stock_code")) {
                        continue;
                    }
                    String[] parts = line.split(",");
                    if (parts.length >= 2) {
                        String code = parts[0].trim();
                        String industry = parts[1].trim();
                        if (!code.isEmpty() && !industry.isEmpty()) {
                            industryMap.put(code, industry);
                            count++;
                        }
                    }
                }
                LOG.info("从 {} 加载了 {} 条行业映射", filePath, count);
                return count > 0;
            } catch (IOException e) {
                LOG.warn("无法从 {} 加载行业映射: {}", filePath, e.getMessage());
                return false;
            }
        }

        @Override
        protected void reduce(Text key, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {

            String stockCode = key.toString().trim();
            // 股票代码标准化补齐（如 "1" → "000001"）
            if (stockCode.length() < 6 && stockCode.matches("\\d+")) {
                stockCode = String.format("%06d", Integer.parseInt(stockCode));
            }
            String industry = industryMap.getOrDefault(stockCode, "其他");

            double sumChange = 0;
            long totalVolume = 0;
            int upCount = 0;
            int downCount = 0;
            int count = 0;

            for (Text val : values) {
                String[] parts = val.toString().split("#");
                if (parts.length >= 4 && "DATA".equals(parts[0])) {
                    try {
                        double change = Double.parseDouble(parts[1]);
                        long vol = Long.parseLong(parts[2]);
                        sumChange += change;
                        totalVolume += vol;
                        if (change > 0) upCount++;
                        else if (change < 0) downCount++;
                        count++;
                    } catch (NumberFormatException e) {
                        context.getCounter("IndustryStatsMR", "PARSE_ERRORS").increment(1);
                    }
                }
            }

            if (count == 0) return;

            double avgChange = Math.round(sumChange / count * 100.0) / 100.0;
            String output = String.format("%s\t%.2f\t%d\t%d\t%d\t%d",
                    industry, avgChange, upCount, downCount, count, totalVolume);
            context.write(new Text(industry), new Text(output));
        }
    }

    // ============================================================
    // 主入口
    // ============================================================
    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (otherArgs.length < 2) {
            System.err.println("用法: IndustryStatsMR <input_path> <output_path> [-files hdfs_industry_mapping_csv]");
            System.err.println("示例:");
            System.err.println("  # 使用分布式缓存（推荐）");
            System.err.println("  hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \\");
            System.err.println("      com.stock.mr.IndustryStatsMR \\");
            System.err.println("      /user/hadoop/stock_data/staging/daily/ \\");
            System.err.println("      /user/hadoop/stock_data/analysis/industry_stats/ \\");
            System.err.println("      -files hdfs:///user/hadoop/stock_data/basic/industry_mapping.csv");
            System.err.println("");
            System.err.println("  # 使用硬编码回退（开发/测试）");
            System.err.println("  hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \\");
            System.err.println("      com.stock.mr.IndustryStatsMR \\");
            System.err.println("      /user/hadoop/stock_data/staging/daily/ \\");
            System.err.println("      /user/hadoop/stock_data/analysis/industry_stats/");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Stock Industry Stats");
        job.setJarByClass(IndustryStatsMR.class);
        job.setMapperClass(IndustryStatsMapper.class);
        job.setReducerClass(IndustryStatsReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        // Mapper 输出以 stock_code 为 key
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(otherArgs[0]));
        FileOutputFormat.setOutputPath(job, new Path(otherArgs[1]));

        // 打印作业配置日志
        LOG.info("=== IndustryStatsMR 启动 ===");
        LOG.info("输入路径: {}", otherArgs[0]);
        LOG.info("输出路径: {}", otherArgs[1]);

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
