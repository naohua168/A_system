#!/bin/sh
for e in /ping /market/list /fund/list /info/cls-news /info/global-news /signal/northbound/latest /signal/hot-reason /market/sector-ranking /index/list /market/industries /market/etf /signal/dragon-tiger/daily /market/industry-treemap /market/markets /signal/fund-flow/600000 /signal/lockup/upcoming /info/research/600000 /info/news/600000 /info/filings/600000 /fund/000006/nav /market/kline/600000; do
  size=$(curl -s -o /dev/null -w "%{size_download}" "http://localhost:8082/api/v2$e")
  if [ "$size" -gt 100 ]; then
    echo "  [OK] $e (${size}B)"
  elif [ "$size" -gt 10 ]; then
    echo "  [EMPTY] $e (${size}B)"
  else
    echo "  [FAIL] $e (${size}B)"
  fi
done
