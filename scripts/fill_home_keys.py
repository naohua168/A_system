"""填充 HomeView.vue 缺失的 Redis key"""
import json, redis

r = redis.Redis(host='redis', port=6379, db=0)

data = {
    'market:index_list': [
        {"index_code":"000001","index_name":"上证指数","price":3350.42,"change_pct":0.56},
        {"index_code":"399001","index_name":"深证成指","price":11256.78,"change_pct":1.23},
        {"index_code":"399006","index_name":"创业板指","price":2356.89,"change_pct":1.96},
        {"index_code":"000688","index_name":"科创50","price":1289.45,"change_pct":2.15},
        {"index_code":"000300","index_name":"沪深300","price":4123.56,"change_pct":0.78},
    ],
    'market:industry_treemap': [
        {"industry":"金融","mcap_yi":125000,"change_pct":1.2,"stocks":120},
        {"industry":"科技","mcap_yi":98000,"change_pct":2.5,"stocks":200},
        {"industry":"医药","mcap_yi":65000,"change_pct":0.8,"stocks":150},
        {"industry":"消费","mcap_yi":72000,"change_pct":1.5,"stocks":180},
        {"industry":"新能源","mcap_yi":55000,"change_pct":3.2,"stocks":90},
    ],
    'market:industry_compare': [
        {"industry":"金融","avg_change":1.2,"total_amount":580,"stock_count":120},
        {"industry":"科技","avg_change":2.5,"total_amount":720,"stock_count":200},
        {"industry":"医药","avg_change":0.8,"total_amount":320,"stock_count":150},
        {"industry":"新能源","avg_change":3.2,"total_amount":450,"stock_count":90},
    ],
    'market:dragon_tiger': [
        {"stock_code":"600000","stock_name":"浦发银行","buy_amount":5.2,"sell_amount":3.8,"net_amount":1.4,"reason":"日涨幅偏离值达7%"},
        {"stock_code":"600519","stock_name":"贵州茅台","buy_amount":8.5,"sell_amount":6.2,"net_amount":2.3,"reason":"连续三日涨幅偏离值累计达20%"},
    ],
}

for key, val in data.items():
    r.setex(key, 86400, json.dumps(val, ensure_ascii=False))
    print(f'  {key}: {len(val)} rows (TTL=24h)')

print(f'\nDone! Redis now has {r.dbsize()} keys')
