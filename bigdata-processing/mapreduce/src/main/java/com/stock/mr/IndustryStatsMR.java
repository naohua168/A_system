/**
 * IndustryStatsMR — 行业统计 MapReduce 作业
 *
 * 输入1: HDFS 上的日K线 CSV (stock_code,date,open,high,low,close,volume,amount,change_pct,turnover)
 * 输入2: HDFS 上的股票基本信息 CSV (code,name,industry,...)
 *
 * 处理流程:
 *   Mapper: 解析CSV → (industry, [change_pct, 1])
 *   Reducer: 聚合 → 行业平均涨跌幅、涨跌家数、总成交额
 *
 * 输出: HDFS /user/hadoop/stock_data/analysis/industry_stats/
 *       industry    avg_change_pct    up_count    down_count    total_volume
 *
 * 执行:
 *   hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       com.stock.mr.IndustryStatsMR \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/industry_stats/
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

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class IndustryStatsMR {

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
                    stockCode = firstField;
                    date = fields[1].trim();
                    changePct = fields.length > 8 ? fields[8].trim() : "0";
                    volume = fields[6].trim();
                } else {
                    // Format B
                    stockCode = fields[fields.length - 1].trim();
                    date = firstField;
                    changePct = fields.length > 8 ? fields[8].trim() : "0";
                    volume = fields[5].trim();
                }

                // 使用stock_code作为中间key，value携带change_pct和volume
                outKey.set(stockCode);
                outValue.set("DATA#" + changePct + "#" + volume + "#" + date);
                context.write(outKey, outValue);

            } catch (Exception e) {
                context.getCounter("IndustryStatsMR", "SKIPPED_LINES").increment(1);
            }
        }
    }

    public static class IndustryStatsReducer
            extends Reducer<Text, Text, Text, Text> {

        // 行业映射表 (临时硬编码，生产环境应使用分布式缓存)
        private static final Map<String, String> INDUSTRY_MAP = new HashMap<>();
        static {
            INDUSTRY_MAP.put("000001", "银行");
            INDUSTRY_MAP.put("600519", "白酒");
            INDUSTRY_MAP.put("300750", "新能源");
            INDUSTRY_MAP.put("000858", "白酒");
            INDUSTRY_MAP.put("600036", "银行");
            INDUSTRY_MAP.put("601318", "保险");
            INDUSTRY_MAP.put("002415", "通信");
            INDUSTRY_MAP.put("300059", "互联网金融");
            INDUSTRY_MAP.put("002463", "半导体");
            INDUSTRY_MAP.put("688017", "高端装备");
        }

        @Override
        protected void reduce(Text key, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {

            String stockCode = key.toString();
            String industry = INDUSTRY_MAP.getOrDefault(stockCode, "其他");

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
                        // skip
                    }
                }
            }

            if (count == 0) return;

            double avgChange = Math.round(sumChange / count * 100.0) / 100.0;
            String output = String.format("%s\t%.2f\t%d\t%d\t%d\t%d",
                    industry, avgChange, upCount, downCount, count, totalVolume);
            context.write(key, new Text(output));
        }
    }

    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (otherArgs.length < 2) {
            System.err.println("用法: IndustryStatsMR <input_path> <output_path>");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Stock Industry Stats");
        job.setJarByClass(IndustryStatsMR.class);
        job.setMapperClass(IndustryStatsMapper.class);
        job.setReducerClass(IndustryStatsReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(otherArgs[0]));
        FileOutputFormat.setOutputPath(job, new Path(otherArgs[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
