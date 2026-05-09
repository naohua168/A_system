/**
 * StockYearlyReturn — 股票年收益率计算 MapReduce 作业
 *
 * 输入: HDFS 上的日K线 CSV (stock_daily_staging 格式)
 *       stock_code,date,open,high,low,close,volume,amount,change_pct,turnover
 *
 * 处理流程:
 *   Mapper: 解析 CSV → (stock_code-year, [date,close])
 *   Reducer: 按年分组 → 排序 → (年末-年初)/年初 × 100%
 *
 * 输出: HDFS /user/hadoop/stock_data/analysis/yearly_return/
 *       stock_code-year    yearly_return
 *
 * 执行:
 *   mvn clean package -P local
 *   hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/yearly_return/
 */

package com.stock.mr;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.DoubleWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.hadoop.util.GenericOptionsParser;

import java.io.IOException;
import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class StockYearlyReturn {

    /**
     * Mapper: 解析 CSV 行 → 输出 (stock_code-year, date#close)
     */
    public static class YearlyReturnMapper
            extends Mapper<Object, Text, Text, Text> {

        private Text outKey = new Text();
        private Text outValue = new Text();

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {

            String line = value.toString().trim();
            // 跳过 CSV 表头
            if (line.startsWith("trade_date") || line.startsWith("date") || line.isEmpty()) {
                return;
            }

            String[] fields = line.split(",");
            if (fields.length < 6) {
                return;
            }

            try {
                // 兼容两种 CSV 格式:
                // 格式A(采集原始): stock_code,date,open,high,low,close,volume,amount,...
                // 格式B(staging):  trade_date,open,high,low,close,volume,amount,...,stock_code
                String stockCode;
                String date;
                double closePrice;

                // 判断格式: 第一个字段如果是纯数字或带字母代码则为格式A
                String firstField = fields[0].trim();
                if (firstField.matches(".*[A-Za-z].*")) {
                    // 格式A: stock_code在第一个字段
                    stockCode = firstField;
                    date = fields[1].trim();
                    closePrice = Double.parseDouble(fields[5].trim());
                } else {
                    // 格式B(分区表临时表): stock_code在最后
                    stockCode = fields[fields.length - 1].trim();
                    date = firstField;
                    closePrice = Double.parseDouble(fields[4].trim());
                }

                // 提取年份
                String year = date.substring(0, 4);
                String compositeKey = stockCode + "-" + year;

                outKey.set(compositeKey);
                outValue.set(date + "#" + closePrice);
                context.write(outKey, outValue);

            } catch (Exception e) {
                // 跳过格式异常的行
                context.getCounter("StockYearlyReturn", "SKIPPED_LINES").increment(1);
            }
        }
    }

    /**
     * Reducer: 按股票+年份 计算年收益率
     *   (年末收盘价 - 年初收盘价) / 年初收盘价 × 100
     */
    public static class YearlyReturnReducer
            extends Reducer<Text, Text, Text, DoubleWritable> {

        private DoubleWritable result = new DoubleWritable();
        private static final DecimalFormat DF = new DecimalFormat("#.00");

        @Override
        protected void reduce(Text key, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {

            // 收集 (date, close) 对
            List<PricePoint> prices = new ArrayList<>();
            for (Text val : values) {
                String[] parts = val.toString().split("#");
                if (parts.length == 2) {
                    prices.add(new PricePoint(parts[0], Double.parseDouble(parts[1])));
                }
            }

            if (prices.size() < 2) {
                context.getCounter("StockYearlyReturn", "INSUFFICIENT_DATA").increment(1);
                return;
            }

            // 按日期升序排序
            Collections.sort(prices);

            // 取年初第一个交易日的收盘价 和 年末最后一个交易日的收盘价
            double firstClose = prices.get(0).close;
            double lastClose = prices.get(prices.size() - 1).close;

            if (firstClose <= 0) {
                context.getCounter("StockYearlyReturn", "ZERO_PRICE").increment(1);
                return;
            }

            double yearlyReturn = (lastClose - firstClose) / firstClose * 100.0;
            result.set(Double.parseDouble(DF.format(yearlyReturn)));
            context.write(key, result);
        }
    }

    // ---- 辅助类 ----

    /** 价格点: 日期 + 收盘价 */
    static class PricePoint implements Comparable<PricePoint> {
        String date;
        double close;

        PricePoint(String date, double close) {
            this.date = date;
            this.close = close;
        }

        @Override
        public int compareTo(PricePoint o) {
            return this.date.compareTo(o.date);
        }
    }

    // ---- 入口 ----

    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (otherArgs.length < 2) {
            System.err.println("用法: StockYearlyReturn <input_path> <output_path>");
            System.err.println("示例: StockYearlyReturn /user/hadoop/stock_data/staging/daily/ /user/hadoop/stock_data/analysis/yearly_return/");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Stock Yearly Return");
        job.setJarByClass(StockYearlyReturn.class);
        job.setMapperClass(YearlyReturnMapper.class);
        job.setReducerClass(YearlyReturnReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(otherArgs[0]));
        FileOutputFormat.setOutputPath(job, new Path(otherArgs[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
