/**
 * VolumeAnalysis — 成交量分析 MapReduce 作业
 *
 * 功能:
 *   1. 计算每只股票月均成交量
 *   2. 标记异常放量（成交量超过月均值 3 倍）
 *
 * 输入: HDFS 上的日K线 CSV (同 StockYearlyReturn 格式)
 * 输出: /user/hadoop/stock_data/analysis/volume/
 *       每行: stock_code-year-month    avg_volume    anomaly_count
 *
 * 执行:
 *   hadoop jar mapreduce-analysis-1.0.0-jar-with-dependencies.jar \
 *       com.stock.mr.VolumeAnalysis \
 *       /user/hadoop/stock_data/staging/daily/ \
 *       /user/hadoop/stock_data/analysis/volume/
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
import java.util.ArrayList;
import java.util.List;

public class VolumeAnalysis {

    /**
     * Mapper: 解析 CSV → (stock_code-year-month, volume)
     */
    public static class VolumeMapper
            extends Mapper<Object, Text, Text, DoubleWritable> {

        private Text outKey = new Text();
        private DoubleWritable outVolume = new DoubleWritable();

        @Override
        protected void map(Object key, Text value, Context context)
                throws IOException, InterruptedException {

            String line = value.toString().trim();
            if (line.startsWith("trade_date") || line.isEmpty()) {
                return;
            }

            String[] fields = line.split(",");
            if (fields.length < 7) return;

            try {
                String stockCode;
                String date;
                double volume;

                String firstField = fields[0].trim();
                if (firstField.matches(".*[A-Za-z].*")) {
                    stockCode = firstField;
                    date = fields[1].trim();
                    volume = Double.parseDouble(fields[6].trim());
                } else {
                    stockCode = fields[fields.length - 1].trim();
                    date = firstField;
                    volume = Double.parseDouble(fields[5].trim());
                }

                // 组合键: stock_code-year-month
                String yearMonth = date.substring(0, 7); // YYYY-MM
                outKey.set(stockCode + "-" + yearMonth);
                outVolume.set(volume);
                context.write(outKey, outVolume);

            } catch (Exception ignored) {
                context.getCounter("VolumeAnalysis", "SKIPPED").increment(1);
            }
        }
    }

    /**
     * Reducer: 计算月均成交量 + 统计异常放量天数
     */
    public static class VolumeReducer
            extends Reducer<Text, DoubleWritable, Text, Text> {

        @Override
        protected void reduce(Text key, Iterable<DoubleWritable> values, Context context)
                throws IOException, InterruptedException {

            List<Double> volumes = new ArrayList<>();
            double sum = 0;
            int count = 0;

            for (DoubleWritable v : values) {
                double vol = v.get();
                volumes.add(vol);
                sum += vol;
                count++;
            }

            if (count == 0) return;

            double avgVolume = sum / count;
            double threshold = avgVolume * 3.0;

            // 统计异常放量天数
            int anomalyDays = 0;
            for (double vol : volumes) {
                if (vol > threshold) {
                    anomalyDays++;
                }
            }

            String result = String.format("%.0f\t%d\t%.2f%%",
                    avgVolume,
                    anomalyDays,
                    (double) anomalyDays / count * 100);

            context.write(key, new Text(result));
        }
    }

    // ---- 入口 ----

    public static void main(String[] args) throws Exception {
        Configuration conf = new Configuration();
        String[] otherArgs = new GenericOptionsParser(conf, args).getRemainingArgs();

        if (otherArgs.length < 2) {
            System.err.println("用法: VolumeAnalysis <input_path> <output_path>");
            System.exit(2);
        }

        Job job = Job.getInstance(conf, "Stock Volume Analysis");
        job.setJarByClass(VolumeAnalysis.class);
        job.setMapperClass(VolumeMapper.class);
        job.setReducerClass(VolumeReducer.class);
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(DoubleWritable.class);
        job.setOutputKeyClass(Text.class);
        job.setOutputValueClass(Text.class);

        FileInputFormat.addInputPath(job, new Path(otherArgs[0]));
        FileOutputFormat.setOutputPath(job, new Path(otherArgs[1]));

        System.exit(job.waitForCompletion(true) ? 0 : 1);
    }
}
