#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from collections import defaultdict

import numpy as np
import pandas as pd

import matplotlib.pyplot as plt

# 支持中文
from matplotlib import ticker
from styleframe import StyleFrame
from tqdm import tqdm

plt.rcParams['font.sans-serif'] = ['Songti SC']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 实验指标
METRICS_MAP = {
    "click_ctr": "点击率",
    "add_ctr": "加购率",
    "order_ctr": "下单率",
    "query_page1_ctr": "首页点击率"
}

# 实验相关分组信息
COMPARE_GROUPS = [532, 533]
EXPERIMENT_GROUPS = [1407, 1408]
GROUP_MAP = {532: "对照组", 533: "对照组", 1407: "实验组", 1408: "实验组"}


def run(PROJECT_NAME, SPLIT_FIELD, SPLIT_MAP):
    data_dir = os.path.join(f"./project/{PROJECT_NAME}/data/{_SPLIT_FIELD}/")

    DATE_METRICS = defaultdict(dict)

    # 词频
    for split in SPLIT_MAP:
        for d in os.listdir(data_dir):
            cur_date = d.split(".")[0]
            data_path = os.path.join(data_dir, d)

            data = pd.read_csv(data_path, sep="\t")

            freq_alias = SPLIT_MAP[split]
            freq_vals = data[data[SPLIT_FIELD] == split]
            cur_date_metric_map = defaultdict(dict)
            # 指标
            for metric in METRICS_MAP:
                metric_alias = METRICS_MAP[metric]
                if metric not in cur_date_metric_map[metric_alias]:
                    cur_date_metric_map[metric_alias] = defaultdict(list)
                # 实验分组
                for g in COMPARE_GROUPS:
                    group_alias = GROUP_MAP[g]
                    freq_group_df = freq_vals[freq_vals["abtp"] == g][metric].values[0]
                    cur_date_metric_map[metric_alias][group_alias].append(freq_group_df)
                cur_date_metric_map[metric_alias][group_alias] = round(
                    np.mean(cur_date_metric_map[metric_alias][group_alias]), 5)
                for g in EXPERIMENT_GROUPS:
                    group_alias = GROUP_MAP[g]
                    freq_group_df = freq_vals[freq_vals["abtp"] == g][metric].values[0]
                    cur_date_metric_map[metric_alias][group_alias].append(freq_group_df)
                cur_date_metric_map[metric_alias][group_alias] = round(
                    np.mean(cur_date_metric_map[metric_alias][group_alias]), 5)
                cur_date_metric_map[metric_alias] = dict(cur_date_metric_map[metric_alias])
            # 指标-分组 拼接
            cur_date_metric_map = {"{}-{}".format(k, v_k): cur_date_metric_map[k][v_k] for k in cur_date_metric_map for v_k
                                   in cur_date_metric_map[k]}
            DATE_METRICS[freq_alias][cur_date] = dict(cur_date_metric_map)
    DATE_METRICS = dict(DATE_METRICS)

    REPORT_DIR = f"./project/{PROJECT_NAME}/report/{SPLIT_FIELD}"
    if not os.path.exists(REPORT_DIR):
        os.mkdir(REPORT_DIR)

    writer = pd.ExcelWriter(f"{REPORT_DIR}/{PROJECT_NAME}_{SPLIT_FIELD}_report.xlsx", mode='w', engine='openpyxl')

    for split_alias in tqdm(DATE_METRICS, desc=f"当前维度{SPLIT_FIELD}分析进度"):
        cur_freq_df = pd.DataFrame(DATE_METRICS[split_alias]).T.sort_index()
        for metric in METRICS_MAP:
            metric_alias = METRICS_MAP[metric]
            cur_freq_df[f"{metric_alias}提升比例"] = (cur_freq_df[f"{metric_alias}-实验组"] - cur_freq_df[f"{metric_alias}-对照组"]) / \
                                                 cur_freq_df[f"{metric_alias}-对照组"]

            # 对比
            bar_width = 0.3
            fig = plt.figure(figsize=(10, 6))
            plt.title(f"{split_alias}-{metric_alias}实验效果")
            ax1 = fig.add_subplot(111)
            x_ticks = [x - bar_width / 2 for x in range(len(cur_freq_df.index))]
            plt.xticks(x_ticks)
            ax1.bar([x for x in x_ticks], width=bar_width, height=cur_freq_df[f"{metric_alias}-对照组"].tolist(), label=f"对照组", alpha=0.8)
            ax1.bar([x + bar_width for x in x_ticks], width=bar_width, height=cur_freq_df[f"{metric_alias}-实验组"].tolist(), label=f"实验组", alpha=0.8)
            ax1.legend(loc="upper left")
            ax1.grid(axis='y', linestyle="-.", alpha=0.3, color="red")
            ax1.set_ylabel("指标")

            # 提升
            ax2 = ax1.twinx()  # 双轴线
            ax2.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1, decimals=2))
            ax2.set_ylabel("提升")
            ax2.plot(cur_freq_df[[f"{metric_alias}提升比例"]], label=f"提升比例", color="red", alpha=0.6)
            plt.hlines(0, min(x_ticks) - bar_width / 2, max(x_ticks) + bar_width, color="green", linestyles="dashed", label="提升基线")  # 横线
            [ax2.text(x - 0.25, y, "{}%".format(round(y * 100.0, 2))) for x, y in enumerate(cur_freq_df[f"{metric_alias}提升比例"])]

            ax2.legend(loc="upper right")

            if not os.path.exists(REPORT_DIR):
                os.mkdir(REPORT_DIR)
            plt.savefig(f"{REPORT_DIR}/{metric_alias}-{split_alias}.png", dpi=300)
            plt.close()

        # excel格式化和sheet写入
        StyleFrame.A_FACTOR = 10.0
        cur_freq_df.insert(0, "日期", cur_freq_df.index.tolist())
        sf = StyleFrame(cur_freq_df)
        sf.to_excel(
            excel_writer=writer,
            sheet_name=split_alias,
            best_fit=cur_freq_df.columns.tolist(),
        )

    writer.save()
    writer.close()


if __name__ == '__main__':
    # 实验名称
    _PROJECT_NAME = "match_recall_20230130"
    # 城市维度分析
    _SPLIT_FIELD = "city_zip"
    _SPLIT_MAP = {0: "总体", 350100: "福州", 350200: "厦门", 420100: "武汉", 440100: "广州", 440300: "深圳", 510100: "成都"}
    run(_PROJECT_NAME, _SPLIT_FIELD, _SPLIT_MAP)

    # 词频维度分析
    _SPLIT_FIELD = "frequency"
    _SPLIT_MAP = {0: "总体", 1: "高频词", 2: "中频词", 3: "低频词"}
    run(_PROJECT_NAME, _SPLIT_FIELD, _SPLIT_MAP)
