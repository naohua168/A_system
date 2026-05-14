/**
 * TechnicalIndicatorMR — 技术指标(MA)计算 MapReduce 作业
 *
 * 输入: HDFS 上的日K线 CSV (按股票分组)
 *       stock_code,date,open,high,low,close,volume,amount
 *
 * 处理流程:
 *   Mapper: 解析CSV → (stock_code, [date,close])
 *   Reducer: 按股票分组 → 排序 → 滑动窗口计算MA5/MA10
 *
 * 输出: HDFS /user/hadoop/stock_data/analysis/technical_ma/
 *       stock_code-date    ma5,ma10,trade_signal
 *
 * 执行:
 *   hadoop jar target/mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       com.stock.mr.TechnicalIndicatorMR \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/technical_ma/
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
import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class TechnicalIndicatorMR {

    public static class TechnicalMapper
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

                outKey.set(stockCode);
                outValue.set(date + "#" + closePrice);
                context.write(outKey, outValue);

            } catch (Exception e) {
                context.getCounter("TechnicalIndicatorMR", "SKIPPED_LINES").increment(1);
            }
        }
    }

    public static class TechnicalReducer
            extends Reducer<Text, Text, Text, Text> {

        private static final DecimalFormat DF = new DecimalFormat("#.00");

        @Override
        protected void reduce(Text key, Iterable<Text> values, Context context)
                throws IOException, InterruptedException {

            // 收集并排序 (date, close)
            List<PricePoint> prices = new ArrayList<>();
            for (Text val : values) {
                String[] parts = val.toString().split("#");
                if (parts.length == 2) {
                    try {
                        prices.add(new PricePoint(parts[0], Double.parseDouble(parts[1])));
                    } catch (NumberFormatException ignored) {}
                }
            }

            Collections.sort(prices);

            if (prices.size() < 10) {
                context.getCounter("TechnicalIndicatorMR", "INSUFFICIENT_DATA").increment(1);
                return;
            }

            // 滑动窗口计算MA5和MA10
            String outputKey = key.toString();
            for (int i = 4; i < prices.size(); i++) {
                double sum5 = 0;
                for (int j = i - 4; j <= i; j++) {
                    sum5 += prices.get(j).close;
                }
                double ma5 = sum5 / 5;

                double ma10 = 0;
                if (i >= 9) {
                    double sum10 = 0;
                    for (int j = i - 9; j <= i; j++) {
                        sum10 += prices.get(j).close;
                    }
                    ma10 = sum10 / 10;
                }

                String signal = "";
                if (i >= 9 && prices.get(i - 1).close < prices.get(i - 1).ma5
                        && prices.get(i).close >= ma5) {
                    signal = "GOLDEN_CROSS";  // 金叉
                } else if (i >= 9 && prices.get(i - 1).close > prices.get(i - 1).ma5
                        && prices.get(i).close <= ma5) {
                    signal = "DEATH_CROSS";   // 死叉
                }

                String outputValue = String.format("%s\t%s\t%s\t%s",
                        prices.get(i).date,
                        DF.format(ma5),
                        i >= 9 ? DF.format(ma10) : "N/A",
                        signal);

                context.write(new Text(outputKey + "-" + prices.get(i).date),
                        new Text(outputValue));
            }
        }
    }

    static class PricePoint implements Comparable<PricePoint> {
        String date;
        double close;
        double ma5;
        double ma10;

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
            System.err.println("用法: TechnicalIndicatorMR <input_path> <output_path>");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Stock Technical Indicator MA");
        job.setJarByClass(TechnicalIndicatorMR.class);
        job.setMapperClass(TechnicalMapper.class);
        job.setReducerClass(TechnicalReducer.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(otherArgs[0]));
        FileOutputFormat.setOutputPath(job, new Path(otherArgs[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
