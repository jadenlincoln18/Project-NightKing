# FINDINGS - Kalshi commodity ladder history

Generated 2026-09-10T17:02:30+00:00 from `data` (period = 1 min). Numbers come from the manifest and the markets/events tables, not from logs.

Manifest: ok=52378 empty=3789 not_found=0 error=0, candles=58,917,335.

## Per series

| series | title | settles on | ladder | events | markets | w/ candles | candles | usable window | months |
|---|---|---|---|---:|---:|---:|---:|---|---:|
| KXWTI | WTI oil on day | ICE | RANGE | 838 | 12348 | 9237 | 8,892,333 | 2022-09..2024-06, 2026-03..2026-09 | 29 |
| KXNATGASD | Natural Gas Daily | Pyth, Trading Economics - Natural Gas, P | CUMUL | 92 | 7762 | 7736 | 5,094,817 | 2026-03..2026-09 | 7 |
| KXSILVERD | Silver daily | Pyth - Silver, Trading Economics - Silve | CUMUL | 95 | 3911 | 3911 | 3,894,687 | 2026-03..2026-09 | 7 |
| KXGOLDD | Gold Daily | Pyth - Gold, Trading Economics - Gold, T | CUMUL | 95 | 3873 | 3873 | 3,882,597 | 2026-03..2026-09 | 7 |
| KXBRENTD | Brent Oil Daily | Pyth, Trading Economics - Brent crude oi | CUMUL | 97 | 2503 | 2494 | 2,660,847 | 2026-03..2026-09 | 7 |
| KXGOLDW | Gold Weekly price  | Pyth - Gold, ICE, Trading Economics - Go | CUMUL | 26 | 1050 | 1050 | 2,568,873 | 2026-03..2026-09 | 7 |
| KXCOPPERD | Daily Copper | Pyth, Trading Economics - Copper Futures | CUMUL | 94 | 4378 | 4378 | 2,558,031 | 2026-03..2026-09 | 7 |
| KXGOLDMON | Gold Monthly Price | Pyth - Gold, ICE, Trading Economics - Go | CUMUL | 8 | 330 | 330 | 2,328,764 | 2026-02..2026-09 | 8 |
| KXWTIW | WTI oil weekly range | ICE | RANGE | 201 | 3119 | 2679 | 2,311,548 | 2022-09..2024-08, 2025-11..2026-09 | 35 |
| KXSILVERMON | Silver Monthly Price | Pyth - Silver, Trading Economics - Silve | CUMUL | 7 | 280 | 280 | 2,185,738 | 2026-03..2026-09 | 7 |
| KXSILVERW | Silver Weekly Price | Pyth - Silver, Trading Economics - Silve | CUMUL | 26 | 1050 | 1050 | 2,037,228 | 2026-03..2026-09 | 7 |
| KXCOPPERW | Copper Weekly Price | Pyth | CUMUL | 21 | 870 | 870 | 1,884,856 | 2026-04..2026-09 | 6 |
| KXAAAGASM | US gas price | AAA | CUMUL | 37 | 470 | 451 | 1,545,017 | 2023-12..2023-12, 2024-02..2024-02, 2024-04..2026-09 | 32 |
| KXBRENTMON | Brent Monthly | Pyth, Trading Economics - Brent crude oi | CUMUL | 6 | 150 | 150 | 1,316,932 | 2026-04..2026-09 | 6 |
| KXBRENTW | Brent Oil | Pyth, Trading Economics - Brent crude oi | CUMUL | 24 | 520 | 520 | 1,316,294 | 2026-03..2026-09 | 7 |
| KXAAAGASW | US gas price up | AAA | CUMUL | 137 | 927 | 906 | 1,171,423 | 2024-07..2024-08, 2024-10..2026-09 | 26 |
| KXCOPPERMON | Copper Monthly Price | Pyth, Trading Economics - Copper Futures | CUMUL | 7 | 290 | 290 | 1,133,970 | 2026-03..2026-09 | 7 |
| KXWTIMAX | WTI oil high | ICE | CUMUL | 7 | 135 | 134 | 1,070,153 | 2023-11..2023-12, 2024-12..2024-12, 2025-09..2025-09, 2025-12..2025-12, 2026-03..2026-04, 2026-07..2026-09 | 10 |
| KXNATGASW | Natural Gas Weekly | Pyth, Trading Economics - Natural Gas | CUMUL | 23 | 949 | 949 | 1,037,258 | 2026-04..2026-09 | 6 |
| KXNATGASMON | Natural Gas Monthly | Pyth, Trading Economics - Natural Gas | CUMUL | 6 | 240 | 240 | 740,995 | 2026-04..2026-09 | 6 |
| KXAAAGASD | US gas price up | AAA | CUMUL | 195 | 3057 | 3055 | 682,814 | 2026-03..2026-09 | 7 |
| KXWTIMIN | WTI oil low | ICE | CUMUL | 7 | 83 | 83 | 436,785 | 2023-03..2023-03, 2023-12..2023-12, 2024-09..2024-09, 2024-12..2024-12, 2025-11..2025-12, 2026-04..2026-04, 2026-06..2026-09 | 11 |
| KXUSGASCPI | US gasoline CPI in [month] | FRED, Trading Economics | CUMUL | 6 | 129 | 129 | 307,392 | 2026-04..2026-09 | 6 |
| KXAAAGASMAXCA | California highest gas price yearly | AAA | CUMUL | 4 | 33 | 33 | 272,406 | 2023-12..2023-12, 2024-07..2024-07, 2024-12..2024-12, 2025-12..2025-12, 2026-02..2026-04, 2026-09..2026-09 | 8 |
| KXGOLDDIRY | GOLDDIRY | Pyth - Gold | CUMUL | 1 | 13 | 13 | 230,859 | 2026-09..2026-09 | 1 |
| KXAAAGASMINCA | California lowest gas price yearly | AAA | CUMUL | 4 | 12 | 12 | 226,571 | 2023-11..2023-11, 2024-11..2024-12, 2025-07..2025-07, 2025-12..2026-01, 2026-09..2026-09 | 7 |
| KXOIL | Price of oil monthly | Energy Information Administration | CUMUL | 10 | 28 | 28 | 225,762 | 2022-03..2022-08 | 6 |
| KXAAAGASMAXTX | Texas highest gas price yearly | AAA | CUMUL | 4 | 27 | 27 | 223,577 | 2024-12..2024-12, 2025-12..2025-12, 2026-02..2026-05, 2026-09..2026-09 | 7 |
| KXAAAGASMAX | US highest gas price yearly | AAA | CUMUL | 4 | 20 | 19 | 214,624 | 2024-12..2024-12, 2026-03..2026-05, 2026-09..2026-09 | 5 |
| KXNGASMAX | Natural gas price peak | Energy Information Administration | CUMUL | 5 | 21 | 21 | 207,483 | 2024-01..2024-01, 2025-01..2025-01, 2025-11..2025-12, 2026-09..2026-09 | 5 |
| KXDIESELW | diesel price week | AAA | CUMUL | 7 | 197 | 176 | 186,121 | 2026-08..2026-09 | 2 |
| KXAAAGASMINTX | Texas lowest gas price yearly | AAA | CUMUL | 4 | 13 | 13 | 184,594 | 2024-12..2024-12, 2025-12..2025-12, 2026-09..2026-09 | 3 |
| KXDIESELD | Daily Diesel Price | AAA | CUMUL | 40 | 894 | 894 | 181,740 | 2026-08..2026-09 | 2 |
| KXCORNW | Corn Weekly | Pyth, Trading Economics - Corn | CUMUL | 4 | 140 | 140 | 172,571 | 2026-04..2026-05 | 2 |
| KXLITHIUMMON | Lithium Monthly | Trading Economics - Lithium | CUMUL | 1 | 40 | 40 | 167,367 | 2026-04..2026-04 | 1 |
| KXNICKELMON | Nickel Monthly | Trading Economics - Nickel | CUMUL | 1 | 40 | 40 | 165,362 | 2026-04..2026-04 | 1 |
| KXOILRIGS | Oil rigs | The American Oil & Gas Reporter, the Ame | CUMUL | 2 | 23 | 23 | 144,303 | 2025-12..2025-12, 2026-09..2026-09 | 2 |
| KXNICKELW | Nickel Weekly | Trading Economics - Nickel | CUMUL | 4 | 170 | 170 | 140,332 | 2026-04..2026-05 | 2 |
| KXSUGARMON | Sugar Monthly | Trading Economics - Sugar | CUMUL | 1 | 34 | 34 | 134,021 | 2026-04..2026-04 | 1 |
| KXCOFFEEW | Weekly Coffee Price | Trading Economics - Coffee | CUMUL | 4 | 126 | 126 | 130,234 | 2026-04..2026-05 | 2 |
| KXLITHIUMW | Lithium Weekly | Trading Economics - Lithium | CUMUL | 4 | 190 | 190 | 129,341 | 2026-04..2026-05 | 2 |
| KXCORNMON | Corn Monthly | Trading Economics - Corn | CUMUL | 1 | 24 | 24 | 125,809 | 2026-04..2026-04 | 1 |
| KXSOLAR | Solar capcity installation | Solar Energy Industries Association | CUMUL | 2 | 10 | 10 | 124,756 | 2026-03..2026-03, 2026-09..2026-09 | 2 |
| KXSUGARW | Sugar Weekly | Trading Economics - Sugar | CUMUL | 4 | 116 | 116 | 123,844 | 2026-04..2026-05 | 2 |
| KXSOYBEANW | Soybean Weekly | Pyth, Trading Economics - Soybeans | CUMUL | 4 | 120 | 120 | 122,543 | 2026-04..2026-05 | 2 |
| KXWHEATMON | Wheat Monthly | Trading Economics - Wheat | CUMUL | 1 | 24 | 24 | 116,986 | 2026-04..2026-04 | 1 |
| KXWHEATW | Wheat Weekly | Pyth, Trading Economics - Wheat | CUMUL | 3 | 92 | 92 | 112,115 | 2026-04..2026-05 | 2 |
| KXLCATTLEMON | Live Cattle Monthly | Trading Economics - Live Cattle | CUMUL | 1 | 24 | 24 | 111,611 | 2026-04..2026-04 | 1 |
| KXWTIMINM | WTI oil monthly low | ICE | CUMUL | 3 | 31 | 31 | 107,739 | 2026-04..2026-06 | 3 |
| KXBTCVSGOLD | BTC vs Gold | CF Benchmarks | ICE, CF Benchmarks | Coi | CUMUL | 3 | 3 | 3 | 105,837 | 2025-11..2025-11, 2026-01..2026-01, 2026-09..2026-09 | 3 |
| KXHOILW | Heating Oil Weekly | Trading Economics - Heating Oil | CUMUL | 4 | 110 | 110 | 105,710 | 2026-04..2026-05 | 2 |
| KXCOFFEEMON | Coffee Monthly | Trading Economics - Coffee | CUMUL | 1 | 20 | 20 | 104,835 | 2026-04..2026-04 | 1 |
| KXDIESELMON | Diesel Prices month | AAA | CUMUL | 2 | 52 | 52 | 104,750 | 2026-08..2026-09 | 2 |
| KXPOWERKWH | Average US electricity price this month | FRED | CUMUL | 4 | 31 | 31 | 104,237 | 2026-06..2026-09 | 4 |
| KXBARRELS | Oil barrels | U.S. Energy Information Administration | | CUMUL | 2 | 11 | 11 | 102,759 | 2025-12..2025-12, 2026-07..2026-07, 2026-09..2026-09 | 3 |
| KXCOCOAW | Cocoa Directional Weekly | Trading Economics - Cocoa | CUMUL | 4 | 90 | 90 | 101,407 | 2026-04..2026-05 | 2 |
| KXSOYBEANMON | Soybean monthly | Trading Economics - Soybeans | CUMUL | 1 | 20 | 20 | 101,064 | 2026-04..2026-04 | 1 |
| KXAAAGASED | US gas price on Election Day | AAA | CUMUL | 1 | 11 | 11 | 98,555 | 2026-09..2026-09 | 1 |
| KXSPRLVL | SPR level on date | U.S. Energy Information Administration,  | CUMUL | 12 | 140 | 140 | 95,996 | 2026-04..2026-04, 2026-07..2026-09 | 4 |
| KXAAAGASMINFL | Florida lowest gas price yearly | AAA | CUMUL | 2 | 7 | 7 | 95,651 | 2025-12..2025-12, 2026-09..2026-09 | 2 |
| KXLCATTLEW | Live Cattle Weekly | Trading Economics - Live Cattle | CUMUL | 4 | 90 | 90 | 94,966 | 2026-04..2026-05 | 2 |
| KXWTIDIRY | WTIDIRY | ICE | CUMUL | 1 | 11 | 11 | 92,478 | 2026-09..2026-09 | 1 |
| KXCOCOAMON | Cocoa Monthly | Trading Economics - Cocoa | CUMUL | 1 | 24 | 24 | 81,744 | 2026-04..2026-04 | 1 |
| KXAAAGASMAXFL | Florida highest gas price yearly | AAA | CUMUL | 2 | 19 | 19 | 78,912 | 2025-12..2025-12, 2026-02..2026-03, 2026-05..2026-05, 2026-09..2026-09 | 5 |
| KXAAAGASMIN | US lowest gas price yearly | AAA | CUMUL | 4 | 15 | 13 | 78,612 | 2023-11..2023-11, 2024-12..2024-12, 2026-07..2026-07, 2026-09..2026-09 | 4 |
| KXAAAGASDFL | Florida gas price | AAA | CUMUL | 17 | 376 | 376 | 78,378 | 2026-08..2026-09 | 2 |
| KXWTIWHEN | WTI When | ICE | CUMUL | 2 | 17 | 17 | 76,994 | 2026-07..2026-09 | 3 |
| KXAAAGASDTX | TX gas price | AAA | CUMUL | 19 | 373 | 373 | 68,928 | 2026-08..2026-09 | 2 |
| KXRHGOLD | RH gold | Robinhood | CUMUL | 8 | 47 | 42 | 68,079 | 2024-10..2024-10, 2025-02..2025-02, 2025-04..2025-05, 2025-07..2025-07, 2025-10..2025-10 | 6 |
| KXJETFUEL | US Gulf Coast jet fuel price weekly | FRED | CUMUL | 12 | 131 | 131 | 67,812 | 2026-04..2026-07 | 4 |
| KXAAAGASDIL | Illinois gas price | AAA | CUMUL | 17 | 309 | 309 | 65,865 | 2026-08..2026-09 | 2 |
| KXHOILMON | Heating Oil Monthly | Trading Economics - Heating Oil | CUMUL | 1 | 20 | 20 | 60,852 | 2026-04..2026-04 | 1 |
| KXAAAGASDOH | Ohio gas price | AAA | CUMUL | 10 | 270 | 270 | 58,356 | 2026-09..2026-09 | 1 |
| KXNGASMIN | Natural gas yearly low | Energy Information Administration | CUMUL | 3 | 14 | 14 | 55,685 | 2023-02..2023-02, 2025-12..2025-12, 2026-05..2026-05, 2026-09..2026-09 | 4 |
| KXNGAS | Natural gas price max and min monthly | Energy Information Administration | CUMUL | 4 | 16 | 16 | 55,612 | 2022-03..2022-03, 2022-06..2022-08 | 4 |
| KXAAAGASDCA | California gas price | AAA | CUMUL | 17 | 309 | 309 | 55,150 | 2026-08..2026-09 | 2 |
| KXDXYVSGOLD | DXY vs. Gold | CNBC | Pyth | RANGE | 1 | 2 | 2 | 51,536 | 2026-09..2026-09 | 1 |
| KXAAAGASDNJ | New Jersey gas prices | AAA | CUMUL | 17 | 326 | 326 | 51,470 | 2026-08..2026-09 | 2 |
| KXGOLDVSSILVER | Gold vs. Silver | Pyth | RANGE | 1 | 2 | 2 | 48,115 | 2026-09..2026-09 | 1 |
| KXAAAGASDWA | Washington gas price | AAA | CUMUL | 10 | 174 | 174 | 44,876 | 2026-09..2026-09 | 1 |
| KXAAAGASWNJ | New Jersey gas price this week | AAA | CUMUL | 3 | 74 | 74 | 42,393 | 2026-08..2026-09 | 2 |
| KXAAAGASDGA | Georgia gas price | AAA | CUMUL | 10 | 182 | 182 | 41,866 | 2026-09..2026-09 | 1 |
| KXTXOIL | Texas crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 4 | 4 | 40,952 | 2026-09..2026-09 | 1 |
| KXDIESELYE | Diesel prices at year end | AAA | CUMUL | 1 | 19 | 19 | 37,536 | 2026-09..2026-09 | 1 |
| KXAAAGASDNY | New York gas price | AAA | CUMUL | 17 | 289 | 289 | 37,456 | 2026-08..2026-09 | 2 |
| KXIRANCRUDE | Iran crude oil production in [month] | OPEC | CUMUL | 4 | 45 | 45 | 37,115 | 2026-07..2026-09 | 3 |
| KXAAAGASDNC | North Carolina gas price | AAA | CUMUL | 10 | 180 | 180 | 36,864 | 2026-09..2026-09 | 1 |
| KXAAAGASDPA | Pennsylvania gas price | AAA | CUMUL | 10 | 210 | 210 | 36,682 | 2026-09..2026-09 | 1 |
| KXILNUCLEAR | Illinois nuclear electricity generation | U.S. Energy Information Administration | CUMUL | 1 | 7 | 7 | 36,333 | 2026-09..2026-09 | 1 |
| KXDIESELELECT | Diesel prices on Election Day | AAA | CUMUL | 1 | 15 | 15 | 34,352 | 2026-09..2026-09 | 1 |
| KXPJMEMERGENCY | PJM capacity emergency days | PJM Interconnection - Emergency Procedur | CUMUL | 1 | 6 | 6 | 33,944 | 2026-09..2026-09 | 1 |
| KXTXERCOTPEAK | Texas ERCOT peak electricity demand | Electric Reliability Council of Texas (E | CUMUL | 1 | 7 | 7 | 30,533 | 2026-09..2026-09 | 1 |
| KXWTIMAXM | WTI oil monthly high | ICE | CUMUL | 1 | 14 | 14 | 30,074 | 2026-06..2026-06 | 1 |
| KXAKPFD | Alaska Permanent Fund Dividend | State of Alaska | CUMUL | 1 | 5 | 5 | 28,663 | 2026-09..2026-09 | 1 |
| KXINXVSBTC | Will the S&P 500 outperform gold this ye | Google Finance | CF Benchmarks | RANGE | 1 | 2 | 2 | 27,725 | 2026-09..2026-09 | 1 |
| KXTXERCOTPEAKD | Texas ERCOT peak electricity demand | Electric Reliability Council of Texas (E | CUMUL | 14 | 175 | 175 | 25,714 | 2026-08..2026-09 | 2 |
| KXDIESELMAXY | Highest U.S. diesel price by year | AAA | CUMUL | 1 | 12 | 12 | 24,876 | 2026-09..2026-09 | 1 |
| KXTRUFGAS | Truflation US CPI Gasoline Price Index | Truflation US CPI Gasoline Price Index | CUMUL | 11 | 165 | 165 | 24,667 | 2026-06..2026-06, 2026-08..2026-08 | 2 |
| KXMEXCUBOIL | Mexico resumes oil exports to Cuba befor | AP | Bloomberg | Reuters | The New York  | CUMUL | 1 | 4 | 4 | 22,287 | 2026-07..2026-09 | 3 |
| KXOILW | Price of oil weekly | Energy Information Administration | CUMUL | 15 | 30 | 30 | 21,969 | 2022-03..2022-08 | 6 |
| KXDIESELMINY | Lowest U.S. diesel price by year | AAA | CUMUL | 1 | 12 | 12 | 21,770 | 2026-09..2026-09 | 1 |
| KXKSWHEAT | Kansas wheat production | USDA National Agricultural Statistics Se | CUMUL | 1 | 8 | 8 | 19,986 | 2026-09..2026-09 | 1 |
| KXWTIVSBRENT | Will the WTI outperform Brent this year? | ICE | Pyth | RANGE | 1 | 2 | 2 | 19,840 | 2026-09..2026-09 | 1 |
| KXOPECCUTS | Oil production cuts | OPEC | OPEC+ | oil ministries of OPEC an | CUMUL | 1 | 1 | 1 | 19,734 | 2026-01..2026-01 | 1 |
| KXSPRMIN | SPRMIN | EIA | CUMUL | 2 | 2 | 2 | 19,534 | 2025-01..2025-01, 2026-01..2026-01 | 2 |
| KXB65 | Beef 65 | USDA | CUMUL | 3 | 33 | 33 | 18,122 | 2026-08..2026-09 | 2 |
| KXINXVSGOLD | Will the S&P 500 outperform gold this ye | Google Finance | Pyth | RANGE | 1 | 2 | 2 | 16,911 | 2026-09..2026-09 | 1 |
| KXB85 | B85 | USDA | CUMUL | 3 | 33 | 33 | 14,890 | 2026-08..2026-09 | 2 |
| KXIAETHANOL | Iowa ethanol production | Iowa Renewable Fuels Association | CUMUL | 1 | 8 | 8 | 14,852 | 2026-09..2026-09 | 1 |
| KXMARCELLUSGAS | Marcellus natural gas production | U.S. Energy Information Administration | CUMUL | 1 | 6 | 6 | 14,791 | 2026-09..2026-09 | 1 |
| KXSDCORNYIELD | South Dakota corn yield | USDA National Agricultural Statistics Se | CUMUL | 1 | 8 | 8 | 14,668 | 2026-09..2026-09 | 1 |
| KXOPUS48OY | Opus 4.8 Output Token | Anthropic | CUMUL | 1 | 4 | 4 | 14,048 | 2026-09..2026-09 | 1 |
| KXWICORNYIELD | Wisconsin corn yield | USDA NASS | CUMUL | 1 | 9 | 9 | 13,688 | 2026-09..2026-09 | 1 |
| KXRIRESPOWER | Rhode Island residential electricity pri | U.S. Energy Information Administration | CUMUL | 1 | 7 | 7 | 13,636 | 2026-09..2026-09 | 1 |
| KXWYCOAL | Wyoming coal production | EIA Quarterly Coal Report | CUMUL | 1 | 8 | 8 | 12,914 | 2026-09..2026-09 | 1 |
| KXAAAGASMAXM | US highest gas price monthly | AAA | CUMUL | 1 | 9 | 9 | 12,908 | 2026-09..2026-09 | 1 |
| KXWVCOAL | West Virginia coal production | EIA Quarterly Coal Report | CUMUL | 1 | 7 | 7 | 12,178 | 2026-09..2026-09 | 1 |
| KXGBT55OY | GPT 5.5 Input Token | OpenAI | CUMUL | 1 | 4 | 4 | 11,088 | 2026-09..2026-09 | 1 |
| KXGOLD | Price of gold | ICE | RANGE | 19 | 95 | 95 | 10,875 | 2022-09..2022-10 | 2 |
| KXAAAGASMINM | US lowest gas price monthly | AAA | CUMUL | 1 | 9 | 9 | 10,498 | 2026-09..2026-09 | 1 |
| KXMSCOTTON | Mississippi cotton production | USDA National Agricultural Statistics Se | CUMUL | 1 | 6 | 6 | 10,267 | 2026-09..2026-09 | 1 |
| KXNGASW | Natural gas price max and min weekly | Energy Information Administration | CUMUL | 5 | 13 | 13 | 9,744 | 2022-07..2022-08 | 2 |
| KXKYCOAL | Kentucky coal production | U.S. Energy Information Administration | CUMUL | 1 | 6 | 6 | 9,450 | 2026-09..2026-09 | 1 |
| KXNECORNYIELD | Nebraska corn yield | USDA National Agricultural Statistics Se | CUMUL | 1 | 5 | 5 | 8,671 | 2026-09..2026-09 | 1 |
| KXAAAGASDTN | Tennessee gas price | AAA | CUMUL | 2 | 44 | 44 | 7,848 | 2026-09..2026-09 | 1 |
| KXINCORNYIELD | Indiana corn yield | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 1 | 7,822 | 2026-09..2026-09 | 1 |
| KXSPRUSE | SPR use | the Department of Energy | the Office of | CUMUL | 1 | 3 | 3 | 7,770 | 2025-07..2025-09 | 3 |
| KXIACORN | Iowa corn production | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 1 | 7,652 | 2026-09..2026-09 | 1 |
| KXVENEZCRUDE | Venezuela crude oil production in [month | OPEC | CUMUL | 1 | 8 | 8 | 7,607 | 2026-09..2026-09 | 1 |
| KXNMCOIL | New Mexico crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 1 | 7,128 | 2026-09..2026-09 | 1 |
| KXGEMINI35OY | Gemini 3.5 Flash Output Token | Google Gemini Developer API pricing | CUMUL | 1 | 4 | 4 | 6,940 | 2026-09..2026-09 | 1 |
| KXAAAGASDVA | Virginia gas price | AAA | CUMUL | 2 | 44 | 44 | 5,387 | 2026-09..2026-09 | 1 |
| KXAAAGASDAZ | Arizona gas price | AAA | CUMUL | 2 | 34 | 34 | 5,339 | 2026-09..2026-09 | 1 |
| KXPAGAS | Pennsylvania natural gas production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 1 | 5,316 | 2026-09..2026-09 | 1 |
| KXAAAGASDMA | Massachusetts gas price | AAA | CUMUL | 2 | 34 | 34 | 4,896 | 2026-09..2026-09 | 1 |
| KXAAAGASDMI | Michigan gas price | AAA | CUMUL | 2 | 34 | 34 | 4,605 | 2026-09..2026-09 | 1 |
| KXNDKOIL | North Dakota crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 1 | 3,782 | 2026-09..2026-09 | 1 |
| KXAKCRUDEOIL | Alaska crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 1 | 3,741 | 2026-09..2026-09 | 1 |
| KXRUCRUDEX | Russia crude exports in [month] below x. | International Energy Agency | CUMUL | 1 | 1 | 1 | 3,711 | 2026-05..2026-05 | 1 |
| KXGEMINI35Y | Gemini 3.5 Flash | Google Gemini Developer API pricing | CUMUL | 1 | 4 | 4 | 3,620 | 2026-09..2026-09 | 1 |
| KXOPUS48Y | Opus 4.8 Input Token | Anthropic | CUMUL | 1 | 4 | 4 | 3,498 | 2026-09..2026-09 | 1 |
| KXGPT55Y | GPT 5.5 Input Token | OpenAI | CUMUL | 1 | 4 | 4 | 3,466 | 2026-09..2026-09 | 1 |
| KXEIACRUDEW | U.S. crude oil inventories | U.S. Energy Information Administration | CUMUL | 2 | 26 | 26 | 2,920 | 2026-09..2026-09 | 1 |
| KXLAOILGASEMP | Louisiana oil and gas extraction employm | Bureau of Labor Statistics | CUMUL | 1 | 1 | 1 | 2,737 | 2026-09..2026-09 | 1 |
| KXDOESPRTENDER | DOE Strategic Petroleum Reserve tenders | the U.S. Department of Energy, Office of | CUMUL | 1 | 3 | 3 | 2,607 | 2026-09..2026-09 | 1 |
| KXNECOF | Nebraska cattle on feed | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 1 | 2,169 | 2026-09..2026-09 | 1 |
| KXVERARELEASE | Vera /rubin release | company | authorized retailers and distr | CUMUL | 1 | 6 | 6 | 1,956 | 2026-09..2026-09 | 1 |
| KXOKOIL | Oklahoma crude oil production | U.S. Energy Information Administration | CUMUL | 1 | 1 | 1 | 1,716 | 2026-09..2026-09 | 1 |
| KXBOEGOLD | BOE gold withdrawals | the BBC | The Guardian | The New York Ti | CUMUL | 1 | 1 | 1 | 1,677 | 2025-05..2025-05 | 1 |
| KXSDCATTLE | South Dakota cattle inventory | USDA NASS | CUMUL | 1 | 1 | 1 | 1,438 | 2026-09..2026-09 | 1 |
| KXAAAEVM | US EV charging price | AAA | CUMUL | 1 | 11 | 11 | 1,238 | 2026-08..2026-08 | 1 |
| KXMTCATTLE | Montana cattle inventory | USDA National Agricultural Statistics Se | CUMUL | 1 | 1 | 1 | 1,238 | 2026-09..2026-09 | 1 |
| KXKEYSTONEFID | Keystone XL final investment decision | South Bow Corporation | CUMUL | 1 | 4 | 4 | 897 | 2026-09..2026-09 | 1 |
| KXCHINAOILINV | China strategic oil inventories | U.S. Energy Information Administration | CUMUL | 1 | 5 | 5 | 775 | 2026-09..2026-09 | 1 |
| KXDIESELM | Diesel price this month | Energy Information Administration | CUMUL | 1 | 10 | 10 | 722 | 2022-11..2022-11 | 1 |
| KXDIESEL | Diesel price this week | Energy Information Administration | CUMUL | 7 | 26 | 26 | 701 | none | 0 |
| KXSTEELMON | Steel Monthly Price | Trading Economics - Steel Rebar Futures | RANGE | 2 | 80 | 40 | 40 | none | 0 |
| KXWHEAT | Average wheat price | United States Department of Agriculture | CUMUL | 1 | 1 | 1 | 31 | none | 0 |
| KXWTIEU | WTI oil up after election | ICE | CUMUL | 1 | 1 | 1 | 15 | none | 0 |
| KXIEAOIL | Will the IEA approve a strategic oil res | International Energy Agency (IEA) | CUMUL | 1 | 1 | 1 | 12 | none | 0 |
| KXWTIE | WTI oil election day | ICE | CUMUL | 1 | 15 | 4 | 10 | none | 0 |
| KXSTEELW | Steel Weekly Price | Trading Economics - Steel Rebar Futures | CUMUL | 2 | 80 | 0 | 0 | none | 0 |

`usable window` = contiguous runs of months in which at least 50% of that month's markets returned candles AND the month averaged at least 50 candles per market. Months outside the runs had markets that existed but barely traded.

## Series by settlement source

- **AAA**: KXAAAEVM, KXAAAGASD, KXAAAGASDAZ, KXAAAGASDCA, KXAAAGASDFL, KXAAAGASDGA, KXAAAGASDIL, KXAAAGASDMA, KXAAAGASDMI, KXAAAGASDNC, KXAAAGASDNJ, KXAAAGASDNY, KXAAAGASDOH, KXAAAGASDPA, KXAAAGASDTN, KXAAAGASDTX, KXAAAGASDVA, KXAAAGASDWA, KXAAAGASED, KXAAAGASM, KXAAAGASMAX, KXAAAGASMAXCA, KXAAAGASMAXFL, KXAAAGASMAXM, KXAAAGASMAXTX, KXAAAGASMIN, KXAAAGASMINCA, KXAAAGASMINFL, KXAAAGASMINM, KXAAAGASMINTX, KXAAAGASW, KXAAAGASWNJ, KXDIESELD, KXDIESELELECT, KXDIESELMAXY, KXDIESELMINY, KXDIESELMON, KXDIESELW, KXDIESELYE
- **U.S. Energy Information Administration**: KXAKCRUDEOIL, KXCHINAOILINV, KXEIACRUDEW, KXILNUCLEAR, KXKYCOAL, KXMARCELLUSGAS, KXNDKOIL, KXNMCOIL, KXOKOIL, KXPAGAS, KXRIRESPOWER, KXSPRLVL, KXTXOIL
- **Pyth**: KXBRENTD, KXBRENTMON, KXBRENTW, KXCOPPERD, KXCOPPERMON, KXCOPPERW, KXCORNW, KXGOLDVSSILVER, KXNATGASD, KXNATGASMON, KXNATGASW, KXSOYBEANW, KXWHEATW
- **ICE** (exchange-settled: CME/ICE option is a candidate hedge): KXGOLD, KXGOLDMON, KXGOLDW, KXWTI, KXWTIDIRY, KXWTIE, KXWTIEU, KXWTIMAX, KXWTIMAXM, KXWTIMIN, KXWTIMINM, KXWTIW, KXWTIWHEN
- **Energy Information Administration**: KXDIESEL, KXDIESELM, KXNGAS, KXNGASMAX, KXNGASMIN, KXNGASW, KXOIL, KXOILW
- **USDA National Agricultural Statistics Service**: KXIACORN, KXINCORNYIELD, KXKSWHEAT, KXMSCOTTON, KXMTCATTLE, KXNECOF, KXNECORNYIELD, KXSDCORNYIELD
- **Pyth - Gold**: KXGOLDD, KXGOLDDIRY, KXGOLDMON, KXGOLDW
- **Trading Economics - Brent crude oil**: KXBRENTD, KXBRENTMON, KXBRENTW
- **Trading Economics - Gold**: KXGOLDD, KXGOLDMON, KXGOLDW
- **FRED**: KXJETFUEL, KXPOWERKWH, KXUSGASCPI
- **Trading Economics - Natural Gas**: KXNATGASD, KXNATGASMON, KXNATGASW
- **Pyth - Silver**: KXSILVERD, KXSILVERMON, KXSILVERW
- **Trading Economics - Silver**: KXSILVERD, KXSILVERMON, KXSILVERW
- **USDA**: KXB65, KXB85
- **Trading Economics - Copper Futures | Trading Economics - Silver | Trading Economics - Brent crude oil | Trading Economics - Steel Rebar Futures**: KXBRENTD, KXGOLDD
- **Trading Economics - Cocoa**: KXCOCOAMON, KXCOCOAW
- **Trading Economics - Coffee**: KXCOFFEEMON, KXCOFFEEW
- **Trading Economics - Copper Futures**: KXCOPPERD, KXCOPPERMON
- **Trading Economics - Corn**: KXCORNMON, KXCORNW
- **OpenAI**: KXGBT55OY, KXGPT55Y
- **Google Gemini Developer API pricing**: KXGEMINI35OY, KXGEMINI35Y
- **Trading Economics - Heating Oil**: KXHOILMON, KXHOILW
- **OPEC**: KXIRANCRUDE, KXVENEZCRUDE
- **Trading Economics - Live Cattle**: KXLCATTLEMON, KXLCATTLEW
- **Trading Economics - Lithium**: KXLITHIUMMON, KXLITHIUMW
- **Trading Economics - Nickel**: KXNICKELMON, KXNICKELW
- **Anthropic**: KXOPUS48OY, KXOPUS48Y
- **USDA NASS**: KXSDCATTLE, KXWICORNYIELD
- **Trading Economics - Soybeans**: KXSOYBEANMON, KXSOYBEANW
- **Trading Economics**: KXSPRLVL, KXUSGASCPI
- **Trading Economics - Steel Rebar Futures**: KXSTEELMON, KXSTEELW
- **Trading Economics - Sugar**: KXSUGARMON, KXSUGARW
- **Electric Reliability Council of Texas (ERCOT)**: KXTXERCOTPEAK, KXTXERCOTPEAKD
- **Trading Economics - Wheat**: KXWHEATMON, KXWHEATW
- **EIA Quarterly Coal Report**: KXWVCOAL, KXWYCOAL
- **State of Alaska**: KXAKPFD
- **U.S. Energy Information Administration | The New York Times | the Associated Press | Bloomberg News | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | NBC**: KXBARRELS
- **the Associated Press | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | EIA**: KXBARRELS
- **the BBC | The Guardian | The New York Times | the Associated Press | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC**: KXBOEGOLD
- **Pyth - Brent**: KXBRENTD
- **CF Benchmarks | ICE** (exchange-settled: CME/ICE option is a candidate hedge): KXBTCVSGOLD
- **CF Benchmarks | CoinDesk | CoinGecko | Coinbase | Bloomberg Terminal | MarketWatch | Yahoo Finance | CNBC | The Wall Street Journal | Financial Times | Bloomberg News | Reuters**: KXBTCVSGOLD
- **Pyth - Copper**: KXCOPPERD
- **the U.S. Department of Energy, Office of Petroleum Reserves**: KXDOESPRTENDER
- **CNBC | Pyth**: KXDXYVSGOLD
- **Iowa Renewable Fuels Association**: KXIAETHANOL
- **International Energy Agency (IEA)**: KXIEAOIL
- **Google Finance | CF Benchmarks**: KXINXVSBTC
- **Google Finance | Pyth**: KXINXVSGOLD
- **South Bow Corporation**: KXKEYSTONEFID
- **Bureau of Labor Statistics**: KXLAOILGASEMP
- **AP | Bloomberg | Reuters | The New York Times | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC News | CBS News | CNN | Fox News | MSNBC | NBC News**: KXMEXCUBOIL
- **Pyth - NATGAS**: KXNATGASD
- **The American Oil & Gas Reporter**: KXOILRIGS
- **the American Oil & Gas reporter**: KXOILRIGS
- **OPEC | OPEC+ | oil ministries of OPEC and OPEC+ member countries | The New York Times | the Associated Press | Bloomberg News | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | NBC | Financial Times | S&P Global Platts | Argus Media | Energy Intelligence | Oil Price Information Service**: KXOPECCUTS
- **PJM Interconnection - Emergency Procedures**: KXPJMEMERGENCY
- **Robinhood**: KXRHGOLD
- **International Energy Agency**: KXRUCRUDEX
- **Solar Energy Industries Association**: KXSOLAR
- **EIA**: KXSPRMIN
- **the Department of Energy | the Office of Petroleum Reserves | the White House | the President of the United States | The New York Times | the Associated Press | Bloomberg News | Reuters | Axios | Politico | Semafor | The Information | The Washington Post | The Wall Street Journal | ABC | CBS | CNN | Fox News | MSNBC | NBC**: KXSPRUSE
- **Truflation US CPI Gasoline Price Index**: KXTRUFGAS
- **company | authorized retailers and distributors of company**: KXVERARELEASE
- **United States Department of Agriculture**: KXWHEAT
- **ICE | Pyth** (exchange-settled: CME/ICE option is a candidate hedge): KXWTIVSBRENT

## Databento shortlist

Series whose dominant settlement source is an exchange, with at least 2 usable months:

- **KXWTI** (ICE) 2022-09..2024-06, 2026-03..2026-09; 29 live months, 8,892,333 candles; front-month contracts seen: WBS 26U-ICE (700), WBS 26V-ICE (570), WBS 26Q-ICE (388)
- **KXWTIW** (ICE) 2022-09..2024-08, 2025-11..2026-09; 35 live months, 2,311,548 candles; front-month contracts seen: WBS 26U-ICE (123), WBS 26V-ICE (108), WBS 26Q-ICE (60)
- **KXWTIMAX** (ICE) 2023-11..2023-12, 2024-12..2024-12, 2025-09..2025-09, 2025-12..2025-12, 2026-03..2026-04, 2026-07..2026-09; 10 live months, 1,070,153 candles; front-month contracts seen: -
- **KXWTIMIN** (ICE) 2023-03..2023-03, 2023-12..2023-12, 2024-09..2024-09, 2024-12..2024-12, 2025-11..2025-12, 2026-04..2026-04, 2026-06..2026-09; 11 live months, 436,785 candles; front-month contracts seen: -
- **KXWTIMINM** (ICE) 2026-04..2026-06; 3 live months, 107,739 candles; front-month contracts seen: -
- **KXBTCVSGOLD** (CF Benchmarks | ICE) 2025-11..2025-11, 2026-01..2026-01, 2026-09..2026-09; 3 live months, 105,837 candles; front-month contracts seen: -
- **KXWTIWHEN** (ICE) 2026-07..2026-09; 3 live months, 76,994 candles; front-month contracts seen: -
- **KXGOLD** (ICE) 2022-09..2022-10; 2 live months, 10,875 candles; front-month contracts seen: -

Buy CME options history covering those windows (plus a month either side for the density fit warm-up). Everything else settles on an aggregated index or has no usable window yet.

## Month-by-month coverage

### KXWTI - WTI oil on day

cadence daily; ladder {"RANGE": 9222, "CUMUL": 3126}; settled 12183, with expiration_value 6900 (markets closing 2022-09 .. 2026-09); ticker formats {"old": 10355, "new": 1993}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-09 | 149 | 0 | 100% | 36,827 | 247 | yes |
| 2022-10 | 170 | 0 | 100% | 36,566 | 215 | yes |
| 2022-11 | 180 | 0 | 100% | 31,003 | 172 | yes |
| 2022-12 | 170 | 0 | 100% | 33,167 | 195 | yes |
| 2023-01 | 160 | 4 | 98% | 23,520 | 147 | yes |
| 2023-02 | 150 | 0 | 100% | 50,263 | 335 | yes |
| 2023-03 | 194 | 0 | 100% | 82,713 | 426 | yes |
| 2023-04 | 160 | 0 | 100% | 40,386 | 252 | yes |
| 2023-05 | 187 | 0 | 100% | 45,019 | 241 | yes |
| 2023-06 | 160 | 0 | 100% | 56,009 | 350 | yes |
| 2023-07 | 160 | 0 | 100% | 51,827 | 324 | yes |
| 2023-08 | 180 | 0 | 100% | 49,103 | 273 | yes |
| 2023-09 | 150 | 0 | 100% | 37,418 | 249 | yes |
| 2023-10 | 180 | 0 | 100% | 53,139 | 295 | yes |
| 2023-11 | 170 | 0 | 100% | 58,493 | 344 | yes |
| 2023-12 | 200 | 0 | 100% | 67,819 | 339 | yes |
| 2024-01 | 255 | 0 | 100% | 80,223 | 315 | yes |
| 2024-02 | 240 | 0 | 100% | 25,260 | 105 | yes |
| 2024-03 | 240 | 0 | 100% | 30,211 | 126 | yes |
| 2024-04 | 270 | 0 | 100% | 23,714 | 88 | yes |
| 2024-05 | 195 | 0 | 100% | 17,330 | 89 | yes |
| 2024-06 | 225 | 0 | 100% | 15,547 | 69 | yes |
| 2024-07 | 270 | 0 | 100% | 13,278 | 49 |  |
| 2024-08 | 255 | 0 | 100% | 8,026 | 31 |  |
| 2024-09 | 247 | 0 | 100% | 1,684 | 7 |  |
| 2024-10 | 315 | 101 | 68% | 2,013 | 6 |  |
| 2024-11 | 300 | 0 | 100% | 2,052 | 7 |  |
| 2024-12 | 315 | 87 | 72% | 2,711 | 9 |  |
| 2025-01 | 330 | 176 | 47% | 235 | 1 |  |
| 2025-02 | 285 | 270 | 5% | 32 | 0 |  |
| 2025-03 | 315 | 236 | 25% | 173 | 1 |  |
| 2025-04 | 330 | 315 | 5% | 25 | 0 |  |
| 2025-05 | 315 | 295 | 6% | 37 | 0 |  |
| 2025-06 | 300 | 266 | 11% | 557 | 2 |  |
| 2025-07 | 330 | 308 | 7% | 43 | 0 |  |
| 2025-08 | 315 | 310 | 2% | 8 | 0 |  |
| 2025-09 | 315 | 297 | 6% | 18 | 0 |  |
| 2025-10 | 330 | 323 | 2% | 15 | 0 |  |
| 2025-11 | 240 | 123 | 49% | 2,481 | 10 |  |
| 2026-03 | 362 | 0 | 100% | 460,816 | 1273 | yes |
| 2026-04 | 501 | 0 | 100% | 894,373 | 1785 | yes |
| 2026-05 | 330 | 0 | 100% | 782,588 | 2371 | yes |
| 2026-06 | 320 | 0 | 100% | 579,837 | 1812 | yes |
| 2026-07 | 628 | 0 | 100% | 982,734 | 1565 | yes |
| 2026-08 | 640 | 0 | 100% | 946,098 | 1478 | yes |
| 2026-09 | 315 | 0 | 100% | 3,266,942 | 10371 | yes |

### KXNATGASD - Natural Gas Daily

cadence daily; ladder {"CUMUL": 7762}; settled 7692, with expiration_value 7592 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 7762}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 190 | 26 | 86% | 52,822 | 278 | yes |
| 2026-04 | 1380 | 0 | 100% | 677,293 | 491 | yes |
| 2026-05 | 1192 | 0 | 100% | 1,041,883 | 874 | yes |
| 2026-06 | 1660 | 0 | 100% | 1,235,539 | 744 | yes |
| 2026-07 | 1450 | 0 | 100% | 1,190,655 | 821 | yes |
| 2026-08 | 1500 | 0 | 100% | 655,957 | 437 | yes |
| 2026-09 | 390 | 0 | 100% | 240,668 | 617 | yes |

### KXSILVERD - Silver daily

cadence daily; ladder {"CUMUL": 3911}; settled 3871, with expiration_value 3871 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 3911}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 253 | 0 | 100% | 157,033 | 621 | yes |
| 2026-04 | 600 | 0 | 100% | 677,188 | 1129 | yes |
| 2026-05 | 650 | 0 | 100% | 704,589 | 1084 | yes |
| 2026-06 | 750 | 0 | 100% | 800,989 | 1068 | yes |
| 2026-07 | 720 | 0 | 100% | 838,478 | 1165 | yes |
| 2026-08 | 698 | 0 | 100% | 559,966 | 802 | yes |
| 2026-09 | 240 | 0 | 100% | 156,444 | 652 | yes |

### KXGOLDD - Gold Daily

cadence daily; ladder {"CUMUL": 3873}; settled 3833, with expiration_value 3833 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 3873}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 253 | 0 | 100% | 223,024 | 882 | yes |
| 2026-04 | 620 | 0 | 100% | 642,117 | 1036 | yes |
| 2026-05 | 610 | 0 | 100% | 629,090 | 1031 | yes |
| 2026-06 | 730 | 0 | 100% | 754,274 | 1033 | yes |
| 2026-07 | 720 | 0 | 100% | 817,304 | 1135 | yes |
| 2026-08 | 700 | 0 | 100% | 638,970 | 913 | yes |
| 2026-09 | 240 | 0 | 100% | 177,818 | 741 | yes |

### KXBRENTD - Brent Oil Daily

cadence daily; ladder {"CUMUL": 2503}; settled 2483, with expiration_value 2463 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 2503}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 223 | 9 | 96% | 83,900 | 376 | yes |
| 2026-04 | 480 | 0 | 100% | 441,243 | 919 | yes |
| 2026-05 | 380 | 0 | 100% | 575,289 | 1514 | yes |
| 2026-06 | 410 | 0 | 100% | 540,881 | 1319 | yes |
| 2026-07 | 470 | 0 | 100% | 548,585 | 1167 | yes |
| 2026-08 | 400 | 0 | 100% | 367,204 | 918 | yes |
| 2026-09 | 140 | 0 | 100% | 103,745 | 741 | yes |

### KXGOLDW - Gold Weekly price 

cadence weekly; ladder {"CUMUL": 1050}; settled 1050, with expiration_value 1010 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 1050}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 120 | 0 | 100% | 187,748 | 1565 | yes |
| 2026-04 | 160 | 0 | 100% | 454,126 | 2838 | yes |
| 2026-05 | 200 | 0 | 100% | 615,183 | 3076 | yes |
| 2026-06 | 170 | 0 | 100% | 404,893 | 2382 | yes |
| 2026-07 | 200 | 0 | 100% | 550,647 | 2753 | yes |
| 2026-08 | 160 | 0 | 100% | 293,285 | 1833 | yes |
| 2026-09 | 40 | 0 | 100% | 62,991 | 1575 | yes |

### KXCOPPERD - Daily Copper

cadence daily; ladder {"CUMUL": 4378}; settled 4328, with expiration_value 4327 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 4378}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 240 | 0 | 100% | 81,870 | 341 | yes |
| 2026-04 | 650 | 0 | 100% | 409,224 | 630 | yes |
| 2026-05 | 650 | 0 | 100% | 445,392 | 685 | yes |
| 2026-06 | 870 | 0 | 100% | 563,501 | 648 | yes |
| 2026-07 | 820 | 0 | 100% | 462,927 | 565 | yes |
| 2026-08 | 850 | 0 | 100% | 449,955 | 529 | yes |
| 2026-09 | 298 | 0 | 100% | 145,162 | 487 | yes |

### KXGOLDMON - Gold Monthly Price

cadence monthly; ladder {"CUMUL": 290, "RANGE": 40}; settled 290, with expiration_value 290 (markets closing 2026-02 .. 2026-08); ticker formats {"new": 330}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-02 | 40 | 0 | 100% | 67,755 | 1694 | yes |
| 2026-03 | 40 | 0 | 100% | 55,531 | 1388 | yes |
| 2026-04 | 40 | 0 | 100% | 575,501 | 14388 | yes |
| 2026-05 | 40 | 0 | 100% | 404,919 | 10123 | yes |
| 2026-06 | 40 | 0 | 100% | 363,952 | 9099 | yes |
| 2026-07 | 40 | 0 | 100% | 488,784 | 12220 | yes |
| 2026-08 | 50 | 0 | 100% | 325,305 | 6506 | yes |
| 2026-09 | 40 | 0 | 100% | 47,017 | 1175 | yes |

### KXWTIW - WTI oil weekly range

cadence weekly; ladder {"RANGE": 3119}; settled 2462, with expiration_value 880 (markets closing 2022-09 .. 2026-09); ticker formats {"old": 2768, "new": 351}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-09 | 15 | 0 | 100% | 6,133 | 409 | yes |
| 2022-10 | 60 | 0 | 100% | 45,545 | 759 | yes |
| 2022-11 | 45 | 0 | 100% | 18,774 | 417 | yes |
| 2022-12 | 75 | 0 | 100% | 41,325 | 551 | yes |
| 2023-01 | 60 | 0 | 100% | 21,128 | 352 | yes |
| 2023-02 | 60 | 0 | 100% | 98,871 | 1648 | yes |
| 2023-03 | 75 | 0 | 100% | 161,151 | 2149 | yes |
| 2023-04 | 45 | 0 | 100% | 22,156 | 492 | yes |
| 2023-05 | 60 | 0 | 100% | 25,741 | 429 | yes |
| 2023-06 | 75 | 0 | 100% | 27,968 | 373 | yes |
| 2023-07 | 60 | 0 | 100% | 27,464 | 458 | yes |
| 2023-08 | 60 | 0 | 100% | 17,574 | 293 | yes |
| 2023-09 | 75 | 0 | 100% | 19,379 | 258 | yes |
| 2023-10 | 60 | 0 | 100% | 10,472 | 175 | yes |
| 2023-11 | 60 | 0 | 100% | 33,551 | 559 | yes |
| 2023-12 | 75 | 0 | 100% | 26,024 | 347 | yes |
| 2024-01 | 60 | 0 | 100% | 13,620 | 227 | yes |
| 2024-02 | 60 | 0 | 100% | 6,939 | 116 | yes |
| 2024-03 | 60 | 0 | 100% | 45,902 | 765 | yes |
| 2024-04 | 60 | 0 | 100% | 52,886 | 881 | yes |
| 2024-05 | 60 | 0 | 100% | 20,927 | 349 | yes |
| 2024-06 | 60 | 0 | 100% | 11,544 | 192 | yes |
| 2024-07 | 60 | 0 | 100% | 10,934 | 182 | yes |
| 2024-08 | 75 | 0 | 100% | 11,340 | 151 | yes |
| 2024-09 | 60 | 0 | 100% | 2,378 | 40 |  |
| 2024-10 | 60 | 0 | 100% | 1,277 | 21 |  |
| 2024-11 | 75 | 0 | 100% | 2,240 | 30 |  |
| 2024-12 | 60 | 15 | 75% | 2,956 | 49 |  |
| 2025-01 | 75 | 18 | 76% | 113 | 2 |  |
| 2025-02 | 60 | 37 | 38% | 99 | 2 |  |
| 2025-03 | 60 | 11 | 82% | 175 | 3 |  |
| 2025-04 | 60 | 42 | 30% | 37 | 1 |  |
| 2025-05 | 75 | 68 | 9% | 11 | 0 |  |
| 2025-06 | 60 | 41 | 32% | 62 | 1 |  |
| 2025-07 | 45 | 26 | 42% | 172 | 4 |  |
| 2025-08 | 75 | 69 | 8% | 11 | 0 |  |
| 2025-09 | 60 | 42 | 30% | 42 | 1 |  |
| 2025-10 | 75 | 60 | 20% | 31 | 0 |  |
| 2025-11 | 60 | 11 | 82% | 3,588 | 60 | yes |
| 2025-12 | 45 | 0 | 100% | 11,430 | 254 | yes |
| 2026-01 | 75 | 0 | 100% | 80,992 | 1080 | yes |
| 2026-02 | 68 | 0 | 100% | 48,177 | 708 | yes |
| 2026-03 | 60 | 0 | 100% | 168,367 | 2806 | yes |
| 2026-04 | 60 | 0 | 100% | 201,710 | 3362 | yes |
| 2026-05 | 75 | 0 | 100% | 315,089 | 4201 | yes |
| 2026-06 | 60 | 0 | 100% | 114,061 | 1901 | yes |
| 2026-07 | 99 | 0 | 100% | 281,962 | 2848 | yes |
| 2026-08 | 108 | 0 | 100% | 205,282 | 1901 | yes |
| 2026-09 | 54 | 0 | 100% | 93,938 | 1740 | yes |

### KXSILVERMON - Silver Monthly Price

cadence monthly; ladder {"CUMUL": 240, "RANGE": 40}; settled 240, with expiration_value 240 (markets closing 2026-03 .. 2026-08); ticker formats {"new": 280}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 40 | 0 | 100% | 54,851 | 1371 | yes |
| 2026-04 | 40 | 0 | 100% | 620,640 | 15516 | yes |
| 2026-05 | 40 | 0 | 100% | 398,499 | 9962 | yes |
| 2026-06 | 40 | 0 | 100% | 398,527 | 9963 | yes |
| 2026-07 | 40 | 0 | 100% | 472,463 | 11812 | yes |
| 2026-08 | 40 | 0 | 100% | 192,330 | 4808 | yes |
| 2026-09 | 40 | 0 | 100% | 48,428 | 1211 | yes |

### KXSILVERW - Silver Weekly Price

cadence weekly; ladder {"CUMUL": 1050}; settled 1050, with expiration_value 1050 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 1050}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 120 | 0 | 100% | 162,386 | 1353 | yes |
| 2026-04 | 170 | 0 | 100% | 373,521 | 2197 | yes |
| 2026-05 | 200 | 0 | 100% | 492,153 | 2461 | yes |
| 2026-06 | 160 | 0 | 100% | 340,713 | 2129 | yes |
| 2026-07 | 200 | 0 | 100% | 428,089 | 2140 | yes |
| 2026-08 | 160 | 0 | 100% | 199,205 | 1245 | yes |
| 2026-09 | 40 | 0 | 100% | 41,161 | 1029 | yes |

### KXCOPPERW - Copper Weekly Price

cadence weekly; ladder {"CUMUL": 870}; settled 830, with expiration_value 830 (markets closing 2026-04 .. 2026-09); ticker formats {"new": 830, "none": 40}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 40 | 0 | 100% | 143,320 | 3583 | yes |
| 2026-05 | 250 | 0 | 100% | 567,244 | 2269 | yes |
| 2026-06 | 180 | 0 | 100% | 346,487 | 1925 | yes |
| 2026-07 | 200 | 0 | 100% | 489,495 | 2447 | yes |
| 2026-08 | 160 | 0 | 100% | 274,199 | 1714 | yes |
| 2026-09 | 40 | 0 | 100% | 64,111 | 1603 | yes |

### KXAAAGASM - US gas price

cadence monthly; ladder {"CUMUL": 470}; settled 425, with expiration_value 423 (markets closing 2023-12 .. 2026-08); ticker formats {"old": 470}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-12 | 1 | 0 | 100% | 146 | 146 | yes |
| 2024-01 | 1 | 0 | 100% | 34 | 34 |  |
| 2024-02 | 1 | 0 | 100% | 85 | 85 | yes |
| 2024-03 | 1 | 0 | 100% | 43 | 43 |  |
| 2024-04 | 1 | 0 | 100% | 156 | 156 | yes |
| 2024-05 | 7 | 0 | 100% | 918 | 131 | yes |
| 2024-06 | 8 | 0 | 100% | 1,317 | 165 | yes |
| 2024-07 | 10 | 0 | 100% | 1,382 | 138 | yes |
| 2024-08 | 10 | 0 | 100% | 1,481 | 148 | yes |
| 2024-09 | 10 | 0 | 100% | 1,212 | 121 | yes |
| 2024-10 | 8 | 0 | 100% | 2,541 | 318 | yes |
| 2024-11 | 5 | 0 | 100% | 14,219 | 2844 | yes |
| 2024-12 | 5 | 0 | 100% | 1,174 | 235 | yes |
| 2025-01 | 6 | 0 | 100% | 2,799 | 466 | yes |
| 2025-02 | 4 | 0 | 100% | 473 | 118 | yes |
| 2025-03 | 5 | 0 | 100% | 24,974 | 4995 | yes |
| 2025-04 | 7 | 0 | 100% | 34,545 | 4935 | yes |
| 2025-05 | 7 | 0 | 100% | 100,939 | 14420 | yes |
| 2025-06 | 11 | 0 | 100% | 117,464 | 10679 | yes |
| 2025-07 | 9 | 0 | 100% | 73,902 | 8211 | yes |
| 2025-08 | 11 | 0 | 100% | 51,238 | 4658 | yes |
| 2025-09 | 10 | 0 | 100% | 36,597 | 3660 | yes |
| 2025-10 | 11 | 0 | 100% | 37,179 | 3380 | yes |
| 2025-11 | 10 | 0 | 100% | 42,379 | 4238 | yes |
| 2025-12 | 10 | 0 | 100% | 63,963 | 6396 | yes |
| 2026-01 | 11 | 0 | 100% | 75,382 | 6853 | yes |
| 2026-02 | 16 | 0 | 100% | 49,005 | 3063 | yes |
| 2026-03 | 34 | 0 | 100% | 165,014 | 4853 | yes |
| 2026-04 | 41 | 0 | 100% | 112,202 | 2737 | yes |
| 2026-05 | 41 | 0 | 100% | 95,087 | 2319 | yes |
| 2026-06 | 33 | 0 | 100% | 78,775 | 2387 | yes |
| 2026-07 | 36 | 0 | 100% | 126,407 | 3511 | yes |
| 2026-08 | 44 | 0 | 100% | 208,447 | 4737 | yes |
| 2026-09 | 33 | 7 | 79% | 23,538 | 713 | yes |
| 2026-10 | 7 | 7 | 0% | 0 | 0 |  |
| 2026-11 | 5 | 5 | 0% | 0 | 0 |  |

### KXBRENTMON - Brent Monthly

cadence monthly; ladder {"CUMUL": 150}; settled 110, with expiration_value 90 (markets closing 2026-04 .. 2026-08); ticker formats {"new": 150}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 20 | 0 | 100% | 225,931 | 11297 | yes |
| 2026-05 | 20 | 0 | 100% | 438,479 | 21924 | yes |
| 2026-06 | 20 | 0 | 100% | 208,123 | 10406 | yes |
| 2026-07 | 30 | 0 | 100% | 256,210 | 8540 | yes |
| 2026-08 | 20 | 0 | 100% | 152,097 | 7605 | yes |
| 2026-09 | 40 | 0 | 100% | 36,092 | 902 | yes |

### KXBRENTW - Brent Oil

cadence weekly; ladder {"CUMUL": 520}; settled 520, with expiration_value 520 (markets closing 2026-03 .. 2026-09); ticker formats {"new": 520}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 20 | 0 | 100% | 26,094 | 1305 | yes |
| 2026-04 | 100 | 0 | 100% | 223,699 | 2237 | yes |
| 2026-05 | 110 | 0 | 100% | 458,086 | 4164 | yes |
| 2026-06 | 80 | 0 | 100% | 160,058 | 2001 | yes |
| 2026-07 | 110 | 0 | 100% | 286,688 | 2606 | yes |
| 2026-08 | 80 | 0 | 100% | 133,935 | 1674 | yes |
| 2026-09 | 20 | 0 | 100% | 27,734 | 1387 | yes |

### KXAAAGASW - US gas price up

cadence weekly; ladder {"CUMUL": 927}; settled 885, with expiration_value 885 (markets closing 2023-10 .. 2026-09); ticker formats {"old": 897, "none": 30}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-10 | 16 | 0 | 100% | 195 | 12 |  |
| 2023-11 | 5 | 0 | 100% | 36 | 7 |  |
| 2023-12 | 4 | 0 | 100% | 132 | 33 |  |
| 2024-01 | 2 | 0 | 100% | 43 | 22 |  |
| 2024-05 | 3 | 0 | 100% | 129 | 43 |  |
| 2024-06 | 4 | 0 | 100% | 127 | 32 |  |
| 2024-07 | 5 | 0 | 100% | 535 | 107 | yes |
| 2024-08 | 4 | 0 | 100% | 340 | 85 | yes |
| 2024-09 | 5 | 0 | 100% | 186 | 37 |  |
| 2024-10 | 4 | 0 | 100% | 684 | 171 | yes |
| 2024-11 | 4 | 0 | 100% | 5,463 | 1366 | yes |
| 2024-12 | 5 | 0 | 100% | 3,319 | 664 | yes |
| 2025-01 | 4 | 0 | 100% | 1,418 | 354 | yes |
| 2025-02 | 4 | 0 | 100% | 2,680 | 670 | yes |
| 2025-03 | 5 | 0 | 100% | 4,728 | 946 | yes |
| 2025-04 | 4 | 0 | 100% | 2,143 | 536 | yes |
| 2025-05 | 4 | 0 | 100% | 5,454 | 1364 | yes |
| 2025-06 | 5 | 0 | 100% | 5,379 | 1076 | yes |
| 2025-07 | 4 | 0 | 100% | 7,802 | 1950 | yes |
| 2025-08 | 4 | 0 | 100% | 6,021 | 1505 | yes |
| 2025-09 | 5 | 0 | 100% | 6,989 | 1398 | yes |
| 2025-10 | 4 | 0 | 100% | 3,986 | 996 | yes |
| 2025-11 | 4 | 0 | 100% | 5,168 | 1292 | yes |
| 2025-12 | 7 | 0 | 100% | 8,177 | 1168 | yes |
| 2026-01 | 8 | 0 | 100% | 25,636 | 3204 | yes |
| 2026-02 | 15 | 0 | 100% | 37,632 | 2509 | yes |
| 2026-03 | 156 | 21 | 87% | 172,454 | 1105 | yes |
| 2026-04 | 89 | 0 | 100% | 131,597 | 1479 | yes |
| 2026-05 | 96 | 0 | 100% | 136,580 | 1423 | yes |
| 2026-06 | 146 | 0 | 100% | 193,080 | 1322 | yes |
| 2026-07 | 98 | 0 | 100% | 197,521 | 2016 | yes |
| 2026-08 | 148 | 0 | 100% | 157,998 | 1068 | yes |
| 2026-09 | 56 | 0 | 100% | 47,791 | 853 | yes |

### KXCOPPERMON - Copper Monthly Price

cadence monthly; ladder {"CUMUL": 250, "RANGE": 40}; settled 240, with expiration_value 240 (markets closing 2026-03 .. 2026-08); ticker formats {"new": 290}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 40 | 0 | 100% | 24,226 | 606 | yes |
| 2026-04 | 40 | 0 | 100% | 116,671 | 2917 | yes |
| 2026-05 | 40 | 0 | 100% | 249,301 | 6233 | yes |
| 2026-06 | 40 | 0 | 100% | 294,441 | 7361 | yes |
| 2026-07 | 40 | 0 | 100% | 222,721 | 5568 | yes |
| 2026-08 | 40 | 0 | 100% | 175,367 | 4384 | yes |
| 2026-09 | 50 | 0 | 100% | 51,243 | 1025 | yes |

### KXWTIMAX - WTI oil high

cadence longer; ladder {"CUMUL": 135}; settled 96, with expiration_value 96 (markets closing 2023-11 .. 2026-09); ticker formats {"old": 135}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-11 | 1 | 0 | 100% | 19,946 | 19946 | yes |
| 2023-12 | 3 | 0 | 100% | 62,969 | 20990 | yes |
| 2024-12 | 4 | 0 | 100% | 43,222 | 10806 | yes |
| 2025-09 | 1 | 0 | 100% | 456 | 456 | yes |
| 2025-12 | 4 | 0 | 100% | 38,390 | 9598 | yes |
| 2026-03 | 5 | 0 | 100% | 15,246 | 3049 | yes |
| 2026-04 | 2 | 0 | 100% | 18,703 | 9352 | yes |
| 2026-07 | 45 | 1 | 98% | 91,383 | 2031 | yes |
| 2026-08 | 20 | 0 | 100% | 103,761 | 5188 | yes |
| 2026-09 | 50 | 0 | 100% | 676,077 | 13522 | yes |

### KXNATGASW - Natural Gas Weekly

cadence weekly; ladder {"CUMUL": 949}; settled 949, with expiration_value 949 (markets closing 2026-04 .. 2026-09); ticker formats {"new": 949}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 170 | 0 | 100% | 209,175 | 1230 | yes |
| 2026-05 | 200 | 0 | 100% | 375,939 | 1880 | yes |
| 2026-06 | 160 | 0 | 100% | 132,798 | 830 | yes |
| 2026-07 | 200 | 0 | 100% | 208,201 | 1041 | yes |
| 2026-08 | 160 | 0 | 100% | 77,867 | 487 | yes |
| 2026-09 | 59 | 0 | 100% | 33,278 | 564 | yes |

### KXNATGASMON - Natural Gas Monthly

cadence monthly; ladder {"CUMUL": 240}; settled 200, with expiration_value 200 (markets closing 2026-04 .. 2026-08); ticker formats {"new": 240}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 40 | 0 | 100% | 40,576 | 1014 | yes |
| 2026-05 | 40 | 0 | 100% | 162,985 | 4075 | yes |
| 2026-06 | 40 | 0 | 100% | 208,709 | 5218 | yes |
| 2026-07 | 40 | 0 | 100% | 241,074 | 6027 | yes |
| 2026-08 | 40 | 0 | 100% | 66,564 | 1664 | yes |
| 2026-09 | 40 | 0 | 100% | 21,087 | 527 | yes |

### KXAAAGASD - US gas price up

cadence daily; ladder {"CUMUL": 3057}; settled 3030, with expiration_value 3030 (markets closing 2023-09 .. 2026-09); ticker formats {"old": 3057}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-09 | 11 | 0 | 100% | 122 | 11 |  |
| 2023-10 | 12 | 1 | 92% | 66 | 6 |  |
| 2024-05 | 2 | 1 | 50% | 4 | 2 |  |
| 2026-03 | 60 | 0 | 100% | 9,538 | 159 | yes |
| 2026-04 | 583 | 0 | 100% | 57,867 | 99 | yes |
| 2026-05 | 584 | 0 | 100% | 173,543 | 297 | yes |
| 2026-06 | 469 | 0 | 100% | 101,693 | 217 | yes |
| 2026-07 | 587 | 0 | 100% | 164,741 | 281 | yes |
| 2026-08 | 530 | 0 | 100% | 122,773 | 232 | yes |
| 2026-09 | 219 | 0 | 100% | 52,467 | 240 | yes |

### KXWTIMIN - WTI oil low

cadence longer; ladder {"CUMUL": 83}; settled 51, with expiration_value 51 (markets closing 2023-03 .. 2026-08); ticker formats {"old": 83}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-03 | 1 | 0 | 100% | 4,006 | 4006 | yes |
| 2023-12 | 3 | 0 | 100% | 53,068 | 17689 | yes |
| 2024-09 | 1 | 0 | 100% | 5,170 | 5170 | yes |
| 2024-12 | 2 | 0 | 100% | 6,078 | 3039 | yes |
| 2025-11 | 2 | 0 | 100% | 1,466 | 733 | yes |
| 2025-12 | 2 | 0 | 100% | 20,283 | 10142 | yes |
| 2026-04 | 1 | 0 | 100% | 2,836 | 2836 | yes |
| 2026-06 | 3 | 0 | 100% | 75,007 | 25002 | yes |
| 2026-07 | 16 | 0 | 100% | 27,450 | 1716 | yes |
| 2026-08 | 20 | 0 | 100% | 40,268 | 2013 | yes |
| 2026-09 | 32 | 0 | 100% | 201,153 | 6286 | yes |

### KXUSGASCPI - US gasoline CPI in [month]

cadence monthly; ladder {"CUMUL": 129}; settled 104, with expiration_value 104 (markets closing 2026-04 .. 2026-08); ticker formats {"old": 129}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 17 | 0 | 100% | 8,457 | 497 | yes |
| 2026-05 | 15 | 0 | 100% | 3,237 | 216 | yes |
| 2026-06 | 22 | 0 | 100% | 83,129 | 3779 | yes |
| 2026-07 | 23 | 0 | 100% | 79,768 | 3468 | yes |
| 2026-08 | 27 | 0 | 100% | 100,517 | 3723 | yes |
| 2026-09 | 25 | 0 | 100% | 32,284 | 1291 | yes |

### KXAAAGASMAXCA - California highest gas price yearly

cadence longer; ladder {"CUMUL": 33}; settled 23, with expiration_value 23 (markets closing 2023-10 .. 2026-04); ticker formats {"old": 33}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-10 | 1 | 0 | 100% | 36 | 36 |  |
| 2023-12 | 1 | 0 | 100% | 374 | 374 | yes |
| 2024-07 | 1 | 0 | 100% | 109 | 109 | yes |
| 2024-12 | 1 | 0 | 100% | 369 | 369 | yes |
| 2025-12 | 1 | 0 | 100% | 35,087 | 35087 | yes |
| 2026-02 | 4 | 0 | 100% | 7,396 | 1849 | yes |
| 2026-03 | 12 | 0 | 100% | 38,767 | 3231 | yes |
| 2026-04 | 2 | 0 | 100% | 6,997 | 3498 | yes |
| 2026-09 | 10 | 0 | 100% | 183,271 | 18327 | yes |

### KXGOLDDIRY - GOLDDIRY

cadence longer; ladder {"CUMUL": 13}; settled 0, with expiration_value 0; ticker formats {"new": 13}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 13 | 0 | 100% | 230,859 | 17758 | yes |

### KXAAAGASMINCA - California lowest gas price yearly

cadence longer; ladder {"CUMUL": 12}; settled 8, with expiration_value 8 (markets closing 2023-11 .. 2026-01); ticker formats {"old": 12}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-11 | 1 | 0 | 100% | 81 | 81 | yes |
| 2024-11 | 1 | 0 | 100% | 181 | 181 | yes |
| 2024-12 | 2 | 0 | 100% | 2,325 | 1162 | yes |
| 2025-07 | 1 | 0 | 100% | 3,962 | 3962 | yes |
| 2025-12 | 2 | 0 | 100% | 101,422 | 50711 | yes |
| 2026-01 | 1 | 0 | 100% | 567 | 567 | yes |
| 2026-09 | 4 | 0 | 100% | 118,033 | 29508 | yes |

### KXOIL - Price of oil monthly

cadence monthly; ladder {"CUMUL": 28}; settled 28, with expiration_value 28 (markets closing 2022-03 .. 2022-08); ticker formats {"old": 28}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-03 | 1 | 0 | 100% | 210 | 210 | yes |
| 2022-04 | 9 | 0 | 100% | 21,787 | 2421 | yes |
| 2022-05 | 4 | 0 | 100% | 3,158 | 790 | yes |
| 2022-06 | 5 | 0 | 100% | 120,466 | 24093 | yes |
| 2022-07 | 4 | 0 | 100% | 38,270 | 9568 | yes |
| 2022-08 | 5 | 0 | 100% | 41,871 | 8374 | yes |

### KXAAAGASMAXTX - Texas highest gas price yearly

cadence longer; ladder {"CUMUL": 27}; settled 17, with expiration_value 17 (markets closing 2023-12 .. 2026-05); ticker formats {"old": 27}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-12 | 2 | 0 | 100% | 13 | 6 |  |
| 2024-12 | 2 | 0 | 100% | 181 | 90 | yes |
| 2025-12 | 2 | 0 | 100% | 80,647 | 40324 | yes |
| 2026-02 | 2 | 0 | 100% | 1,273 | 636 | yes |
| 2026-03 | 7 | 0 | 100% | 18,956 | 2708 | yes |
| 2026-04 | 1 | 0 | 100% | 2,531 | 2531 | yes |
| 2026-05 | 1 | 0 | 100% | 4,862 | 4862 | yes |
| 2026-09 | 10 | 0 | 100% | 115,114 | 11511 | yes |

### KXAAAGASMAX - US highest gas price yearly

cadence longer; ladder {"CUMUL": 20}; settled 7, with expiration_value 6 (markets closing 2023-12 .. 2026-05); ticker formats {"old": 20}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-12 | 1 | 0 | 100% | 7 | 7 |  |
| 2024-12 | 2 | 0 | 100% | 4,146 | 2073 | yes |
| 2025-12 | 1 | 1 | 0% | 0 | 0 |  |
| 2026-03 | 1 | 0 | 100% | 322 | 322 | yes |
| 2026-04 | 1 | 0 | 100% | 2,580 | 2580 | yes |
| 2026-05 | 1 | 0 | 100% | 4,697 | 4697 | yes |
| 2026-09 | 13 | 0 | 100% | 202,872 | 15606 | yes |

### KXNGASMAX - Natural gas price peak

cadence longer; ladder {"CUMUL": 21}; settled 14, with expiration_value 14 (markets closing 2024-01 .. 2025-12); ticker formats {"old": 19, "none": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2024-01 | 6 | 0 | 100% | 37,340 | 6223 | yes |
| 2025-01 | 4 | 0 | 100% | 36,002 | 9000 | yes |
| 2025-11 | 2 | 0 | 100% | 616 | 308 | yes |
| 2025-12 | 2 | 0 | 100% | 3,038 | 1519 | yes |
| 2026-09 | 7 | 0 | 100% | 130,487 | 18641 | yes |

### KXDIESELW - diesel price week

cadence weekly; ladder {"CUMUL": 197}; settled 145, with expiration_value 145 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 197}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 115 | 21 | 82% | 100,878 | 877 | yes |
| 2026-09 | 82 | 0 | 100% | 85,243 | 1040 | yes |

### KXAAAGASMINTX - Texas lowest gas price yearly

cadence longer; ladder {"CUMUL": 13}; settled 7, with expiration_value 7 (markets closing 2023-10 .. 2025-12); ticker formats {"old": 13}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-10 | 1 | 0 | 100% | 28 | 28 |  |
| 2024-12 | 3 | 0 | 100% | 1,293 | 431 | yes |
| 2025-12 | 3 | 0 | 100% | 87,531 | 29177 | yes |
| 2026-09 | 6 | 0 | 100% | 95,742 | 15957 | yes |

### KXDIESELD - Daily Diesel Price

cadence daily; ladder {"CUMUL": 894}; settled 873, with expiration_value 873 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 894}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 619 | 0 | 100% | 122,946 | 199 | yes |
| 2026-09 | 275 | 0 | 100% | 58,794 | 214 | yes |

### KXCORNW - Corn Weekly

cadence weekly; ladder {"CUMUL": 140}; settled 140, with expiration_value 120 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 140}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 100 | 0 | 100% | 114,509 | 1145 | yes |
| 2026-05 | 40 | 0 | 100% | 58,062 | 1452 | yes |

### KXLITHIUMMON - Lithium Monthly

cadence monthly; ladder {"CUMUL": 40}; settled 40, with expiration_value 40 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 40}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 40 | 0 | 100% | 167,367 | 4184 | yes |

### KXNICKELMON - Nickel Monthly

cadence monthly; ladder {"CUMUL": 40}; settled 40, with expiration_value 40 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 40}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 40 | 0 | 100% | 165,362 | 4134 | yes |

### KXOILRIGS - Oil rigs

cadence unknown; ladder {"CUMUL": 23}; settled 11, with expiration_value 11 (markets closing 2025-12 .. 2025-12); ticker formats {"none": 23}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-12 | 11 | 0 | 100% | 134,735 | 12249 | yes |
| 2026-09 | 12 | 0 | 100% | 9,568 | 797 | yes |

### KXNICKELW - Nickel Weekly

cadence weekly; ladder {"CUMUL": 170}; settled 170, with expiration_value 131 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 170}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 130 | 0 | 100% | 112,675 | 867 | yes |
| 2026-05 | 40 | 0 | 100% | 27,657 | 691 | yes |

### KXSUGARMON - Sugar Monthly

cadence monthly; ladder {"CUMUL": 34}; settled 34, with expiration_value 34 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 34}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 34 | 0 | 100% | 134,021 | 3942 | yes |

### KXCOFFEEW - Weekly Coffee Price

cadence weekly; ladder {"CUMUL": 126}; settled 126, with expiration_value 126 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 126}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 92 | 0 | 100% | 82,198 | 893 | yes |
| 2026-05 | 34 | 0 | 100% | 48,036 | 1413 | yes |

### KXLITHIUMW - Lithium Weekly

cadence weekly; ladder {"CUMUL": 190}; settled 190, with expiration_value 151 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 190}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 140 | 0 | 100% | 98,939 | 707 | yes |
| 2026-05 | 50 | 0 | 100% | 30,402 | 608 | yes |

### KXCORNMON - Corn Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 24 | 0 | 100% | 125,809 | 5242 | yes |

### KXSOLAR - Solar capcity installation

cadence unknown; ladder {"CUMUL": 10}; settled 5, with expiration_value 5 (markets closing 2026-03 .. 2026-03); ticker formats {"none": 10}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 5 | 0 | 100% | 113,868 | 22774 | yes |
| 2026-09 | 5 | 0 | 100% | 10,888 | 2178 | yes |

### KXSUGARW - Sugar Weekly

cadence weekly; ladder {"CUMUL": 116}; settled 116, with expiration_value 92 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 116}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 82 | 0 | 100% | 82,979 | 1012 | yes |
| 2026-05 | 34 | 0 | 100% | 40,865 | 1202 | yes |

### KXSOYBEANW - Soybean Weekly

cadence weekly; ladder {"CUMUL": 120}; settled 120, with expiration_value 120 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 120}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 90 | 0 | 100% | 88,235 | 980 | yes |
| 2026-05 | 30 | 0 | 100% | 34,308 | 1144 | yes |

### KXWHEATMON - Wheat Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 24 | 0 | 100% | 116,986 | 4874 | yes |

### KXWHEATW - Wheat Weekly

cadence monthly; ladder {"CUMUL": 92}; settled 92, with expiration_value 92 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 92}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 58 | 0 | 100% | 68,764 | 1186 | yes |
| 2026-05 | 34 | 0 | 100% | 43,351 | 1275 | yes |

### KXLCATTLEMON - Live Cattle Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 24 | 0 | 100% | 111,611 | 4650 | yes |

### KXWTIMINM - WTI oil monthly low

cadence monthly; ladder {"CUMUL": 31}; settled 31, with expiration_value 31 (markets closing 2026-04 .. 2026-06); ticker formats {"old": 31}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 12 | 0 | 100% | 43,602 | 3634 | yes |
| 2026-05 | 5 | 0 | 100% | 30,850 | 6170 | yes |
| 2026-06 | 14 | 0 | 100% | 33,287 | 2378 | yes |

### KXBTCVSGOLD - BTC vs Gold

cadence unknown; ladder {"CUMUL": 3}; settled 2, with expiration_value 2 (markets closing 2025-11 .. 2026-01); ticker formats {"none": 3}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-11 | 1 | 0 | 100% | 28,211 | 28211 | yes |
| 2026-01 | 1 | 0 | 100% | 11,041 | 11041 | yes |
| 2026-09 | 1 | 0 | 100% | 66,585 | 66585 | yes |

### KXHOILW - Heating Oil Weekly

cadence weekly; ladder {"CUMUL": 110}; settled 110, with expiration_value 91 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 110}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 90 | 0 | 100% | 71,085 | 790 | yes |
| 2026-05 | 20 | 0 | 100% | 34,625 | 1731 | yes |

### KXCOFFEEMON - Coffee Monthly

cadence monthly; ladder {"CUMUL": 20}; settled 20, with expiration_value 20 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 20}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 20 | 0 | 100% | 104,835 | 5242 | yes |

### KXDIESELMON - Diesel Prices month

cadence unknown; ladder {"CUMUL": 52}; settled 21, with expiration_value 21 (markets closing 2026-08 .. 2026-08); ticker formats {"old": 52}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 21 | 0 | 100% | 39,551 | 1883 | yes |
| 2026-09 | 31 | 0 | 100% | 65,199 | 2103 | yes |

### KXPOWERKWH - Average US electricity price this month

cadence monthly; ladder {"CUMUL": 31}; settled 24, with expiration_value 24 (markets closing 2026-06 .. 2026-08); ticker formats {"old": 31}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-06 | 6 | 0 | 100% | 3,982 | 664 | yes |
| 2026-07 | 11 | 0 | 100% | 69,417 | 6311 | yes |
| 2026-08 | 7 | 0 | 100% | 23,725 | 3389 | yes |
| 2026-09 | 7 | 0 | 100% | 7,113 | 1016 | yes |

### KXBARRELS - Oil barrels

cadence unknown; ladder {"CUMUL": 11}; settled 7, with expiration_value 7 (markets closing 2025-12 .. 2026-07); ticker formats {"none": 11}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-12 | 4 | 0 | 100% | 77,621 | 19405 | yes |
| 2026-07 | 3 | 0 | 100% | 8,547 | 2849 | yes |
| 2026-09 | 4 | 0 | 100% | 16,591 | 4148 | yes |

### KXCOCOAW - Cocoa Directional Weekly

cadence weekly; ladder {"CUMUL": 90}; settled 90, with expiration_value 90 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 90}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 70 | 0 | 100% | 61,944 | 885 | yes |
| 2026-05 | 20 | 0 | 100% | 39,463 | 1973 | yes |

### KXSOYBEANMON - Soybean monthly

cadence monthly; ladder {"CUMUL": 20}; settled 20, with expiration_value 20 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 20}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 20 | 0 | 100% | 101,064 | 5053 | yes |

### KXAAAGASED - US gas price on Election Day

cadence unknown; ladder {"CUMUL": 11}; settled 0, with expiration_value 0; ticker formats {"old": 11}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 11 | 0 | 100% | 98,555 | 8960 | yes |

### KXSPRLVL - SPR level on date

cadence weekly; ladder {"CUMUL": 140}; settled 128, with expiration_value 128 (markets closing 2026-04 .. 2026-09); ticker formats {"old": 140}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 21 | 0 | 100% | 28,644 | 1364 | yes |
| 2026-07 | 37 | 0 | 100% | 31,652 | 855 | yes |
| 2026-08 | 56 | 0 | 100% | 20,552 | 367 | yes |
| 2026-09 | 26 | 0 | 100% | 15,148 | 583 | yes |

### KXAAAGASMINFL - Florida lowest gas price yearly

cadence longer; ladder {"CUMUL": 7}; settled 3, with expiration_value 3 (markets closing 2025-12 .. 2026-01); ticker formats {"old": 7}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-12 | 2 | 0 | 100% | 9,205 | 4602 | yes |
| 2026-01 | 1 | 0 | 100% | 27 | 27 |  |
| 2026-09 | 4 | 0 | 100% | 86,419 | 21605 | yes |

### KXLCATTLEW - Live Cattle Weekly

cadence weekly; ladder {"CUMUL": 90}; settled 90, with expiration_value 90 (markets closing 2026-04 .. 2026-05); ticker formats {"new": 90}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 60 | 0 | 100% | 64,269 | 1071 | yes |
| 2026-05 | 30 | 0 | 100% | 30,697 | 1023 | yes |

### KXWTIDIRY - WTIDIRY

cadence longer; ladder {"CUMUL": 11}; settled 0, with expiration_value 0; ticker formats {"new": 11}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 11 | 0 | 100% | 92,478 | 8407 | yes |

### KXCOCOAMON - Cocoa Monthly

cadence monthly; ladder {"CUMUL": 24}; settled 24, with expiration_value 24 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 24}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 24 | 0 | 100% | 81,744 | 3406 | yes |

### KXAAAGASMAXFL - Florida highest gas price yearly

cadence longer; ladder {"CUMUL": 19}; settled 12, with expiration_value 12 (markets closing 2025-12 .. 2026-05); ticker formats {"old": 19}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-12 | 2 | 0 | 100% | 8,128 | 4064 | yes |
| 2026-02 | 1 | 0 | 100% | 154 | 154 | yes |
| 2026-03 | 7 | 0 | 100% | 11,834 | 1691 | yes |
| 2026-05 | 2 | 0 | 100% | 5,705 | 2852 | yes |
| 2026-09 | 7 | 0 | 100% | 53,091 | 7584 | yes |

### KXAAAGASMIN - US lowest gas price yearly

cadence longer; ladder {"CUMUL": 15}; settled 6, with expiration_value 4 (markets closing 2023-11 .. 2026-07); ticker formats {"old": 15}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-11 | 1 | 0 | 100% | 65 | 65 | yes |
| 2024-12 | 2 | 0 | 100% | 1,233 | 616 | yes |
| 2025-12 | 2 | 2 | 0% | 0 | 0 |  |
| 2026-07 | 1 | 0 | 100% | 8,950 | 8950 | yes |
| 2026-09 | 9 | 0 | 100% | 68,364 | 7596 | yes |

### KXAAAGASDFL - Florida gas price

cadence daily; ladder {"CUMUL": 376}; settled 359, with expiration_value 359 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 376}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 113 | 0 | 100% | 18,645 | 165 | yes |
| 2026-09 | 263 | 0 | 100% | 59,733 | 227 | yes |

### KXWTIWHEN - WTI When

cadence unknown; ladder {"CUMUL": 17}; settled 8, with expiration_value 8 (markets closing 2026-07 .. 2026-08); ticker formats {"none": 17}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-07 | 6 | 0 | 100% | 27,655 | 4609 | yes |
| 2026-08 | 5 | 0 | 100% | 28,723 | 5745 | yes |
| 2026-09 | 6 | 0 | 100% | 20,616 | 3436 | yes |

### KXAAAGASDTX - TX gas price

cadence daily; ladder {"CUMUL": 373}; settled 346, with expiration_value 346 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 373}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 136 | 0 | 100% | 18,427 | 135 | yes |
| 2026-09 | 237 | 0 | 100% | 50,501 | 213 | yes |

### KXRHGOLD - RH gold

cadence unknown; ladder {"CUMUL": 47}; settled 47, with expiration_value 42 (markets closing 2024-05 .. 2025-10); ticker formats {"none": 47}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2024-05 | 10 | 5 | 50% | 263 | 26 |  |
| 2024-08 | 8 | 0 | 100% | 343 | 43 |  |
| 2024-10 | 5 | 0 | 100% | 373 | 75 | yes |
| 2025-02 | 5 | 0 | 100% | 19,268 | 3854 | yes |
| 2025-04 | 1 | 0 | 100% | 2,238 | 2238 | yes |
| 2025-05 | 8 | 0 | 100% | 8,697 | 1087 | yes |
| 2025-07 | 3 | 0 | 100% | 22,691 | 7564 | yes |
| 2025-10 | 7 | 0 | 100% | 14,206 | 2029 | yes |

### KXJETFUEL - US Gulf Coast jet fuel price weekly

cadence weekly; ladder {"CUMUL": 131}; settled 131, with expiration_value 131 (markets closing 2026-04 .. 2026-07); ticker formats {"old": 131}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 24 | 0 | 100% | 7,999 | 333 | yes |
| 2026-05 | 44 | 0 | 100% | 22,186 | 504 | yes |
| 2026-06 | 44 | 0 | 100% | 27,829 | 632 | yes |
| 2026-07 | 19 | 0 | 100% | 9,798 | 516 | yes |

### KXAAAGASDIL - Illinois gas price

cadence daily; ladder {"CUMUL": 309}; settled 292, with expiration_value 292 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 309}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 102 | 0 | 100% | 19,320 | 189 | yes |
| 2026-09 | 207 | 0 | 100% | 46,545 | 225 | yes |

### KXHOILMON - Heating Oil Monthly

cadence monthly; ladder {"CUMUL": 20}; settled 20, with expiration_value 20 (markets closing 2026-04 .. 2026-04); ticker formats {"new": 20}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-04 | 20 | 0 | 100% | 60,852 | 3043 | yes |

### KXAAAGASDOH - Ohio gas price

cadence daily; ladder {"CUMUL": 270}; settled 243, with expiration_value 243 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 270}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 270 | 0 | 100% | 58,356 | 216 | yes |

### KXNGASMIN - Natural gas yearly low

cadence longer; ladder {"CUMUL": 14}; settled 9, with expiration_value 9 (markets closing 2023-01 .. 2026-05); ticker formats {"old": 14}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2023-01 | 3 | 0 | 100% | 73 | 24 |  |
| 2023-02 | 1 | 0 | 100% | 502 | 502 | yes |
| 2025-12 | 3 | 0 | 100% | 6,570 | 2190 | yes |
| 2026-05 | 2 | 0 | 100% | 2,905 | 1452 | yes |
| 2026-09 | 5 | 0 | 100% | 45,635 | 9127 | yes |

### KXNGAS - Natural gas price max and min monthly

cadence monthly; ladder {"CUMUL": 16}; settled 16, with expiration_value 16 (markets closing 2022-03 .. 2022-08); ticker formats {"old": 16}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-03 | 1 | 0 | 100% | 293 | 293 | yes |
| 2022-04 | 2 | 0 | 100% | 26 | 13 |  |
| 2022-06 | 4 | 0 | 100% | 3,514 | 878 | yes |
| 2022-07 | 6 | 0 | 100% | 29,643 | 4940 | yes |
| 2022-08 | 3 | 0 | 100% | 22,136 | 7379 | yes |

### KXAAAGASDCA - California gas price

cadence daily; ladder {"CUMUL": 309}; settled 292, with expiration_value 292 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 309}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 102 | 0 | 100% | 18,106 | 178 | yes |
| 2026-09 | 207 | 0 | 100% | 37,044 | 179 | yes |

### KXDXYVSGOLD - DXY vs. Gold

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 2 | 0 | 100% | 51,536 | 25768 | yes |

### KXAAAGASDNJ - New Jersey gas prices

cadence daily; ladder {"CUMUL": 326}; settled 299, with expiration_value 299 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 326}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 102 | 0 | 100% | 14,047 | 138 | yes |
| 2026-09 | 224 | 0 | 100% | 37,423 | 167 | yes |

### KXGOLDVSSILVER - Gold vs. Silver

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 2 | 0 | 100% | 48,115 | 24058 | yes |

### KXAAAGASDWA - Washington gas price

cadence daily; ladder {"CUMUL": 174}; settled 157, with expiration_value 157 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 174}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 174 | 0 | 100% | 44,876 | 258 | yes |

### KXAAAGASWNJ - New Jersey gas price this week

cadence weekly; ladder {"CUMUL": 74}; settled 53, with expiration_value 53 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 74}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 21 | 0 | 100% | 30,988 | 1476 | yes |
| 2026-09 | 53 | 0 | 100% | 11,405 | 215 | yes |

### KXAAAGASDGA - Georgia gas price

cadence daily; ladder {"CUMUL": 182}; settled 165, with expiration_value 165 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 182}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 182 | 0 | 100% | 41,866 | 230 | yes |

### KXTXOIL - Texas crude oil production

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"old": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 40,952 | 10238 | yes |

### KXDIESELYE - Diesel prices at year end

cadence longer; ladder {"CUMUL": 19}; settled 0, with expiration_value 0; ticker formats {"old": 19}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 19 | 0 | 100% | 37,536 | 1976 | yes |

### KXAAAGASDNY - New York gas price

cadence daily; ladder {"CUMUL": 289}; settled 272, with expiration_value 272 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 289}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 102 | 0 | 100% | 10,236 | 100 | yes |
| 2026-09 | 187 | 0 | 100% | 27,220 | 146 | yes |

### KXIRANCRUDE - Iran crude oil production in [month]

cadence monthly; ladder {"CUMUL": 45}; settled 34, with expiration_value 34 (markets closing 2026-07 .. 2026-09); ticker formats {"old": 45}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-07 | 12 | 0 | 100% | 20,620 | 1718 | yes |
| 2026-08 | 11 | 0 | 100% | 10,195 | 927 | yes |
| 2026-09 | 22 | 0 | 100% | 6,300 | 286 | yes |

### KXAAAGASDNC - North Carolina gas price

cadence daily; ladder {"CUMUL": 180}; settled 163, with expiration_value 163 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 180}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 180 | 0 | 100% | 36,864 | 205 | yes |

### KXAAAGASDPA - Pennsylvania gas price

cadence daily; ladder {"CUMUL": 210}; settled 193, with expiration_value 193 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 210}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 210 | 0 | 100% | 36,682 | 175 | yes |

### KXILNUCLEAR - Illinois nuclear electricity generation

cadence longer; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 7 | 0 | 100% | 36,333 | 5190 | yes |

### KXDIESELELECT - Diesel prices on Election Day

cadence unknown; ladder {"CUMUL": 15}; settled 0, with expiration_value 0; ticker formats {"old": 15}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 15 | 0 | 100% | 34,352 | 2290 | yes |

### KXPJMEMERGENCY - PJM capacity emergency days

cadence longer; ladder {"CUMUL": 6}; settled 1, with expiration_value 1 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 6}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 6 | 0 | 100% | 33,944 | 5657 | yes |

### KXTXERCOTPEAK - Texas ERCOT peak electricity demand

cadence unknown; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 7 | 0 | 100% | 30,533 | 4362 | yes |

### KXWTIMAXM - WTI oil monthly high

cadence monthly; ladder {"CUMUL": 14}; settled 14, with expiration_value 14 (markets closing 2026-06 .. 2026-06); ticker formats {"old": 14}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-06 | 14 | 0 | 100% | 30,074 | 2148 | yes |

### KXAKPFD - Alaska Permanent Fund Dividend

cadence longer; ladder {"CUMUL": 5}; settled 0, with expiration_value 0; ticker formats {"old": 5}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 5 | 0 | 100% | 28,663 | 5733 | yes |

### KXINXVSBTC - Will the S&P 500 outperform gold this year?

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 2 | 0 | 100% | 27,725 | 13862 | yes |

### KXTXERCOTPEAKD - Texas ERCOT peak electricity demand

cadence daily; ladder {"CUMUL": 175}; settled 163, with expiration_value 163 (markets closing 2026-08 .. 2026-09); ticker formats {"old": 175}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 35 | 0 | 100% | 4,380 | 125 | yes |
| 2026-09 | 140 | 0 | 100% | 21,334 | 152 | yes |

### KXDIESELMAXY - Highest U.S. diesel price by year

cadence longer; ladder {"CUMUL": 12}; settled 0, with expiration_value 0; ticker formats {"old": 12}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 12 | 0 | 100% | 24,876 | 2073 | yes |

### KXTRUFGAS - Truflation US CPI Gasoline Price Index

cadence daily; ladder {"CUMUL": 165}; settled 165, with expiration_value 165 (markets closing 2026-06 .. 2026-08); ticker formats {"old": 165}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-06 | 150 | 0 | 100% | 12,581 | 84 | yes |
| 2026-08 | 15 | 0 | 100% | 12,086 | 806 | yes |

### KXMEXCUBOIL - Mexico resumes oil exports to Cuba before date

cadence unknown; ladder {"CUMUL": 4}; settled 2, with expiration_value 2 (markets closing 2026-07 .. 2026-08); ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-07 | 1 | 0 | 100% | 18,862 | 18862 | yes |
| 2026-08 | 1 | 0 | 100% | 944 | 944 | yes |
| 2026-09 | 2 | 0 | 100% | 2,481 | 1240 | yes |

### KXOILW - Price of oil weekly

cadence weekly; ladder {"CUMUL": 30}; settled 30, with expiration_value 30 (markets closing 2022-03 .. 2022-08); ticker formats {"old": 30}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-03 | 8 | 0 | 100% | 2,597 | 325 | yes |
| 2022-04 | 4 | 0 | 100% | 8,343 | 2086 | yes |
| 2022-05 | 4 | 0 | 100% | 2,616 | 654 | yes |
| 2022-06 | 4 | 0 | 100% | 3,189 | 797 | yes |
| 2022-07 | 4 | 0 | 100% | 1,547 | 387 | yes |
| 2022-08 | 6 | 0 | 100% | 3,677 | 613 | yes |

### KXDIESELMINY - Lowest U.S. diesel price by year

cadence longer; ladder {"CUMUL": 12}; settled 0, with expiration_value 0; ticker formats {"old": 12}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 12 | 0 | 100% | 21,770 | 1814 | yes |

### KXKSWHEAT - Kansas wheat production

cadence longer; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 8 | 0 | 100% | 19,986 | 2498 | yes |

### KXWTIVSBRENT - Will the WTI outperform Brent this year?

cadence unknown; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 2 | 0 | 100% | 19,840 | 9920 | yes |

### KXOPECCUTS - Oil production cuts

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2026-01 .. 2026-01); ticker formats {"none": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-01 | 1 | 0 | 100% | 19,734 | 19734 | yes |

### KXSPRMIN - SPRMIN

cadence unknown; ladder {"CUMUL": 2}; settled 2, with expiration_value 2 (markets closing 2025-01 .. 2026-01); ticker formats {"none": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-01 | 1 | 0 | 100% | 2,605 | 2605 | yes |
| 2026-01 | 1 | 0 | 100% | 16,929 | 16929 | yes |

### KXB65 - Beef 65

cadence unknown; ladder {"CUMUL": 33}; settled 22, with expiration_value 22 (markets closing 2026-08 .. 2026-09); ticker formats {"none": 33}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 11 | 0 | 100% | 6,996 | 636 | yes |
| 2026-09 | 22 | 0 | 100% | 11,126 | 506 | yes |

### KXINXVSGOLD - Will the S&P 500 outperform gold this year?

cadence longer; ladder {"RANGE": 2}; settled 0, with expiration_value 0; ticker formats {"old": 2}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 2 | 0 | 100% | 16,911 | 8456 | yes |

### KXB85 - B85

cadence unknown; ladder {"CUMUL": 33}; settled 22, with expiration_value 22 (markets closing 2026-08 .. 2026-09); ticker formats {"none": 33}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 11 | 0 | 100% | 5,107 | 464 | yes |
| 2026-09 | 22 | 0 | 100% | 9,783 | 445 | yes |

### KXIAETHANOL - Iowa ethanol production

cadence longer; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 8 | 0 | 100% | 14,852 | 1856 | yes |

### KXMARCELLUSGAS - Marcellus natural gas production

cadence longer; ladder {"CUMUL": 6}; settled 0, with expiration_value 0; ticker formats {"old": 6}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 6 | 0 | 100% | 14,791 | 2465 | yes |

### KXSDCORNYIELD - South Dakota corn yield

cadence longer; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 8 | 0 | 100% | 14,668 | 1834 | yes |

### KXOPUS48OY - Opus 4.8 Output Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 14,048 | 3512 | yes |

### KXWICORNYIELD - Wisconsin corn yield

cadence unknown; ladder {"CUMUL": 9}; settled 0, with expiration_value 0; ticker formats {"old": 9}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 9 | 0 | 100% | 13,688 | 1521 | yes |

### KXRIRESPOWER - Rhode Island residential electricity price

cadence longer; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 7 | 0 | 100% | 13,636 | 1948 | yes |

### KXWYCOAL - Wyoming coal production

cadence unknown; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 8 | 0 | 100% | 12,914 | 1614 | yes |

### KXAAAGASMAXM - US highest gas price monthly

cadence monthly; ladder {"CUMUL": 9}; settled 1, with expiration_value 1 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 9}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 9 | 0 | 100% | 12,908 | 1434 | yes |

### KXWVCOAL - West Virginia coal production

cadence longer; ladder {"CUMUL": 7}; settled 0, with expiration_value 0; ticker formats {"old": 7}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 7 | 0 | 100% | 12,178 | 1740 | yes |

### KXGBT55OY - GPT 5.5 Input Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 11,088 | 2772 | yes |

### KXGOLD - Price of gold

cadence daily; ladder {"RANGE": 95}; settled 95, with expiration_value 19 (markets closing 2022-09 .. 2022-10); ticker formats {"new": 95}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-09 | 75 | 0 | 100% | 8,486 | 113 | yes |
| 2022-10 | 20 | 0 | 100% | 2,389 | 119 | yes |

### KXAAAGASMINM - US lowest gas price monthly

cadence monthly; ladder {"CUMUL": 9}; settled 0, with expiration_value 0; ticker formats {"old": 9}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 9 | 0 | 100% | 10,498 | 1166 | yes |

### KXMSCOTTON - Mississippi cotton production

cadence longer; ladder {"CUMUL": 6}; settled 0, with expiration_value 0; ticker formats {"old": 6}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 6 | 0 | 100% | 10,267 | 1711 | yes |

### KXNGASW - Natural gas price max and min weekly

cadence weekly; ladder {"CUMUL": 13}; settled 13, with expiration_value 13 (markets closing 2022-07 .. 2022-08); ticker formats {"old": 13}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-07 | 7 | 0 | 100% | 5,169 | 738 | yes |
| 2022-08 | 6 | 0 | 100% | 4,575 | 762 | yes |

### KXKYCOAL - Kentucky coal production

cadence longer; ladder {"CUMUL": 6}; settled 0, with expiration_value 0; ticker formats {"old": 6}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 6 | 0 | 100% | 9,450 | 1575 | yes |

### KXNECORNYIELD - Nebraska corn yield

cadence longer; ladder {"CUMUL": 5}; settled 0, with expiration_value 0; ticker formats {"old": 5}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 5 | 0 | 100% | 8,671 | 1734 | yes |

### KXAAAGASDTN - Tennessee gas price

cadence daily; ladder {"CUMUL": 44}; settled 27, with expiration_value 27 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 44}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 44 | 0 | 100% | 7,848 | 178 | yes |

### KXINCORNYIELD - Indiana corn yield

cadence unknown; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 7,822 | 7822 | yes |

### KXSPRUSE - SPR use

cadence unknown; ladder {"CUMUL": 3}; settled 3, with expiration_value 3 (markets closing 2025-07 .. 2025-09); ticker formats {"none": 3}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-07 | 1 | 0 | 100% | 935 | 935 | yes |
| 2025-08 | 1 | 0 | 100% | 2,843 | 2843 | yes |
| 2025-09 | 1 | 0 | 100% | 3,992 | 3992 | yes |

### KXIACORN - Iowa corn production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 7,652 | 7652 | yes |

### KXVENEZCRUDE - Venezuela crude oil production in [month]

cadence monthly; ladder {"CUMUL": 8}; settled 0, with expiration_value 0; ticker formats {"old": 8}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 8 | 0 | 100% | 7,607 | 951 | yes |

### KXNMCOIL - New Mexico crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 7,128 | 7128 | yes |

### KXGEMINI35OY - Gemini 3.5 Flash Output Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 6,940 | 1735 | yes |

### KXAAAGASDVA - Virginia gas price

cadence daily; ladder {"CUMUL": 44}; settled 27, with expiration_value 27 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 44}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 44 | 0 | 100% | 5,387 | 122 | yes |

### KXAAAGASDAZ - Arizona gas price

cadence daily; ladder {"CUMUL": 34}; settled 17, with expiration_value 17 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 34}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 34 | 0 | 100% | 5,339 | 157 | yes |

### KXPAGAS - Pennsylvania natural gas production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 5,316 | 5316 | yes |

### KXAAAGASDMA - Massachusetts gas price

cadence daily; ladder {"CUMUL": 34}; settled 17, with expiration_value 17 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 34}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 34 | 0 | 100% | 4,896 | 144 | yes |

### KXAAAGASDMI - Michigan gas price

cadence daily; ladder {"CUMUL": 34}; settled 17, with expiration_value 17 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 34}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 34 | 0 | 100% | 4,605 | 135 | yes |

### KXNDKOIL - North Dakota crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 3,782 | 3782 | yes |

### KXAKCRUDEOIL - Alaska crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 3,741 | 3741 | yes |

### KXRUCRUDEX - Russia crude exports in [month] below x.x mbpd?

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2026-05 .. 2026-05); ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-05 | 1 | 0 | 100% | 3,711 | 3711 | yes |

### KXGEMINI35Y - Gemini 3.5 Flash

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 3,620 | 905 | yes |

### KXOPUS48Y - Opus 4.8 Input Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 3,498 | 874 | yes |

### KXGPT55Y - GPT 5.5 Input Token

cadence longer; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 3,466 | 866 | yes |

### KXEIACRUDEW - U.S. crude oil inventories

cadence weekly; ladder {"CUMUL": 26}; settled 13, with expiration_value 13 (markets closing 2026-09 .. 2026-09); ticker formats {"old": 26}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 26 | 0 | 100% | 2,920 | 112 | yes |

### KXLAOILGASEMP - Louisiana oil and gas extraction employment

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 2,737 | 2737 | yes |

### KXDOESPRTENDER - DOE Strategic Petroleum Reserve tenders

cadence unknown; ladder {"CUMUL": 3}; settled 0, with expiration_value 0; ticker formats {"none": 3}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 3 | 0 | 100% | 2,607 | 869 | yes |

### KXNECOF - Nebraska cattle on feed

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 2,169 | 2169 | yes |

### KXVERARELEASE - Vera /rubin release

cadence unknown; ladder {"CUMUL": 6}; settled 2, with expiration_value 2 (markets closing 2026-08 .. 2026-09); ticker formats {"none": 6}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 1 | 0 | 100% | 46 | 46 |  |
| 2026-09 | 5 | 0 | 100% | 1,910 | 382 | yes |

### KXOKOIL - Oklahoma crude oil production

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 1,716 | 1716 | yes |

### KXBOEGOLD - BOE gold withdrawals

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2025-05 .. 2025-05); ticker formats {"none": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2025-05 | 1 | 0 | 100% | 1,677 | 1677 | yes |

### KXSDCATTLE - South Dakota cattle inventory

cadence unknown; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 1,438 | 1438 | yes |

### KXAAAEVM - US EV charging price

cadence monthly; ladder {"CUMUL": 11}; settled 11, with expiration_value 11 (markets closing 2026-08 .. 2026-08); ticker formats {"old": 11}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-08 | 11 | 0 | 100% | 1,238 | 113 | yes |

### KXMTCATTLE - Montana cattle inventory

cadence longer; ladder {"CUMUL": 1}; settled 0, with expiration_value 0; ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 1 | 0 | 100% | 1,238 | 1238 | yes |

### KXKEYSTONEFID - Keystone XL final investment decision

cadence unknown; ladder {"CUMUL": 4}; settled 0, with expiration_value 0; ticker formats {"none": 4}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 4 | 0 | 100% | 897 | 224 | yes |

### KXCHINAOILINV - China strategic oil inventories

cadence unknown; ladder {"CUMUL": 5}; settled 0, with expiration_value 0; ticker formats {"old": 5}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-09 | 5 | 0 | 100% | 775 | 155 | yes |

### KXDIESELM - Diesel price this month

cadence monthly; ladder {"CUMUL": 10}; settled 10, with expiration_value 10 (markets closing 2022-11 .. 2022-11); ticker formats {"old": 10}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-11 | 10 | 0 | 100% | 722 | 72 | yes |

### KXDIESEL - Diesel price this week

cadence weekly; ladder {"CUMUL": 26}; settled 26, with expiration_value 26 (markets closing 2022-10 .. 2022-12); ticker formats {"old": 26}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-10 | 9 | 0 | 100% | 297 | 33 |  |
| 2022-11 | 9 | 0 | 100% | 194 | 22 |  |
| 2022-12 | 8 | 0 | 100% | 210 | 26 |  |

### KXSTEELMON - Steel Monthly Price

cadence monthly; ladder {"RANGE": 80}; settled 40, with expiration_value 11 (markets closing 2026-03 .. 2026-03); ticker formats {"new": 40, "none": 40}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 80 | 40 | 50% | 40 | 0 |  |

### KXWHEAT - Average wheat price

cadence monthly; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2022-04 .. 2022-04); ticker formats {"none": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2022-04 | 1 | 0 | 100% | 31 | 31 |  |

### KXWTIEU - WTI oil up after election

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2024-11 .. 2024-11); ticker formats {"old": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2024-11 | 1 | 0 | 100% | 15 | 15 |  |

### KXIEAOIL - Will the IEA approve a strategic oil reserves release?

cadence unknown; ladder {"CUMUL": 1}; settled 1, with expiration_value 1 (markets closing 2026-03 .. 2026-03); ticker formats {"none": 1}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 1 | 0 | 100% | 12 | 12 |  |

### KXWTIE - WTI oil election day

cadence unknown; ladder {"CUMUL": 15}; settled 15, with expiration_value 15 (markets closing 2024-11 .. 2024-11); ticker formats {"old": 15}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2024-11 | 15 | 11 | 27% | 10 | 1 |  |

### KXSTEELW - Steel Weekly Price

cadence weekly; ladder {"CUMUL": 80}; settled 0, with expiration_value 0; ticker formats {"new": 40, "none": 40}

| month | markets | zero-candle | % with candles | candles | per market | live |
|---|---:|---:|---:|---:|---:|:---:|
| 2026-03 | 80 | 80 | 0% | 0 | 0 |  |
