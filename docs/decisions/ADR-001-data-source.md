# ADR-001: Data Source Selection

**Status:** Draft  
**Date:** 2026-09-02

## Context
Need reproducible, open exchange rate data for RUB → TJS/UZS/KGS/AMD/KZT corridors.

## Decision
Primary source: CBR RF daily rates (XML API).
- URL: `https://www.cbr.ru/scripts/XML_daily.asp?date_req=DD/MM/YYYY`
- Fields: date, currency code, nominal, rate in RUB
- History: available from 1992

Secondary sources (if higher granularity needed):
- Moscow Exchange (MOEX) — intraday, open API
- Must remain open and reproducible — document source in code

## Consequences
- Must normalize denominations before any computation
- Weekend/holiday gaps → forward-fill + flag `is_trading_day`
- 1-day publication lag: rate for day T published on T, but refers to T+1 (verify this)
- All raw downloads saved to `data/raw/`, never modified
