/**
 * MonthlyReturnMR — 股票月收益率计算 MapReduce 作业
 *
 * 输入: HDFS 上的日K线 CSV
 *       stock_code,date,open,high,low,close,volume,amount,change_pct,turnover
 *
 * 处理流程:
 *   Mapper: 解析 CSV → (stock_code-year-month, [date,close])
 *   Reducer: 按月分组 → 排序 → (月末-月初)/月初 × 100%
 *
 * 输出: HDFS /user/hadoop/stock_data/analysis/monthly_return/
 *       stock_code-year-month    monthly_return
 *
 * 执行:
 *   hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       com.stock.mr.MonthlyReturnMR \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/monthly_return/
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

public class MonthlyReturnMR {

    public static class MonthlyReturnMapper
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
                String date;
                double closePrice;

                String firstField = fields[0].trim();
                if (firstField.matches(".*[A-Za-z].*")) {
                    stockCode = firstField;
                    date = fields[1].trim();
                    closePrice = Double.parseDouble(fields[5].trim());
                } else {
                    stockCode = fields[fields.length - 1].trim();
                    date = firstField;
                    closePrice = Double.parseDouble(fields[4].trim());
                }

                String year = date.substring(0, 4);
                String month = date.substring(5, 7);
                outKey.set(stockCode + "-" + year + "-" + month);
                outValue.set(date + "#" + closePrice);
                context.write(outKey, outValue);

            } catch (Exception e) {
                context.getCounter("MonthlyReturnMR", "SKIPPED_LINES").increment(1);
            }
        }
    }

    public static class MonthlyReturnReducer
            extends Reducer<Text, Text, Text, DoubleWritable> {

        private DoubleWritable result = new DoubleWritable();
        private static final DecimalFormat DF = new DecimalFormat("#.00");

        @Override
        protected void reduce(Text key, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {

            List<PricePoint> prices = new ArrayList<>();
            for (Text val : values) {
                String[] parts = val.toString().split("#");
                if (parts.length == 2) {
                    prices.add(new PricePoint(parts[0], Double.parseDouble(parts[1])));
                }
            }

            if (prices.size() < 2) {
                context.getCounter("MonthlyReturnMR", "INSUFFICIENT_DATA").increment(1);
                return;
            }

            Collections.sort(prices);

            double firstClose = prices.get(0).close;
            double lastClose = prices.get(prices.size() - 1).close;

            if (firstClose <= 0) {
                context.getCounter("MonthlyReturnMR", "ZERO_PRICE").increment(1);
                return;
            }

            double monthlyReturn = (lastClose - firstClose) / firstClose * 100.0;
            result.set(Double.parseDouble(DF.format(monthlyReturn)));
            context.write(key, result);
        }
    }

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

    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (otherArgs.length < 2) {
            System.err.println("用法: MonthlyReturnMR <input_path> <output_path>");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Stock Monthly Return");
        job.setJarByClass(MonthlyReturnMR.class);
        job.setMapperClass(MonthlyReturnMapper.class);
        job.setReducerClass(MonthlyReturnReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(otherArgs[0]));
        FileOutputFormat.setOutputPath(job, new Path(otherArgs[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
