"""Notebook/实验输出模块

提供 Jupyter notebook 友好的输出格式和可视化工具。
支持：
- HTML 展示
- DataFrame 转换
- 图表生成
- 实验结果对比
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExperimentRecord:
    """实验记录"""

    id: str
    name: str
    timestamp: float
    urls: List[str]
    schema: Dict[str, Any]
    results: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExperimentTracker:
    """实验跟踪器

    用于管理和对比多次实验的结果。

    使用示例:
        tracker = ExperimentTracker()

        # 记录实验
        tracker.record("experiment-1", urls, results)

        # 对比实验
        comparison = tracker.compare()
    """

    def __init__(self) -> None:
        self.experiments: List[ExperimentRecord] = []

    def record(
        self,
        name: str,
        urls: List[str],
        results: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExperimentRecord:
        """记录一次实验

        Args:
            name: 实验名称
            urls: URL 列表
            results: 结果列表
            schema: 提取 schema
            metadata: 额外元数据

        Returns:
            ExperimentRecord: 实验记录
        """
        record = ExperimentRecord(
            id=f"exp-{len(self.experiments) + 1:03d}",
            name=name,
            timestamp=time.time(),
            urls=urls,
            schema=schema or {},
            results=results,
            metadata=metadata or {},
        )
        self.experiments.append(record)
        return record

    def get_experiment(self, name: str) -> Optional[ExperimentRecord]:
        """获取指定名称的实验"""
        for exp in self.experiments:
            if exp.name == name:
                return exp
        return None

    def compare(self) -> Dict[str, Any]:
        """对比所有实验的结果

        Returns:
            Dict: 对比结果
        """
        comparison = {
            "experiments": [],
            "summary": {
                "total_experiments": len(self.experiments),
                "total_urls": sum(len(exp.urls) for exp in self.experiments),
                "total_results": sum(len(exp.results) for exp in self.experiments),
            },
        }

        for exp in self.experiments:
            exp_summary = {
                "id": exp.id,
                "name": exp.name,
                "urls_count": len(exp.urls),
                "results_count": len(exp.results),
                "success_rate": self._calculate_success_rate(exp.results),
                "avg_extract_time": self._avg_extract_time(exp.results),
            }
            comparison["experiments"].append(exp_summary)

        return comparison

    def to_dataframe(self) -> Any:
        """将所有实验结果转换为 DataFrame

        Returns:
            pd.DataFrame: 数据框
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for DataFrame conversion")

        rows = []
        for exp in self.experiments:
            for result in exp.results:
                row = {
                    "experiment_id": exp.id,
                    "experiment_name": exp.name,
                    "seed": result.get("seed"),
                    "extract": json.dumps(result.get("extract", {})),
                    "duration_ms": result.get("duration_ms"),
                    "error": result.get("error"),
                }
                rows.append(row)

        return pd.DataFrame(rows)

    def _calculate_success_rate(self, results: List[Dict[str, Any]]) -> float:
        """计算成功率"""
        if not results:
            return 0.0
        success_count = sum(1 for r in results if not r.get("error"))
        return success_count / len(results) * 100

    def _avg_extract_time(self, results: List[Dict[str, Any]]) -> float:
        """计算平均提取时间"""
        if not results:
            return 0.0
        times = [r.get("duration_ms", 0) for r in results if r.get("duration_ms")]
        return sum(times) / len(times) if times else 0.0


# Notebook 可视化函数


def display_experiment_table(experiments: List[ExperimentRecord]) -> None:
    """在 notebook 中展示实验表格

    Args:
        experiments: 实验记录列表
    """
    try:
        from IPython.display import display, HTML

        html = """
        <table style="border-collapse: collapse; width: 100%;">
            <thead>
                <tr style="background: #f0f0f0;">
                    <th style="border: 1px solid #ddd; padding: 8px;">ID</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">URLs</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Results</th>
                    <th style="border: 1px solid #ddd; padding: 8px;">Success Rate</th>
                </tr>
            </thead>
            <tbody>
        """

        for exp in experiments:
            success_rate = (
                sum(1 for r in exp.results if not r.get("error"))
                / len(exp.results)
                * 100
                if exp.results
                else 0
            )

            html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{exp.id}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{exp.name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{len(exp.urls)}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{len(exp.results)}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{success_rate:.1f}%</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        """

        display(HTML(html))
    except ImportError:
        # 非 notebook 环境，打印文本
        print(f"{'ID':<10} {'Name':<20} {'URLs':<6} {'Results':<8}")
        print("-" * 50)
        for exp in experiments:
            print(
                f"{exp.id:<10} {exp.name:<20} {len(exp.urls):<6} {len(exp.results):<8}"
            )


def display_extract_comparison(results: List[Dict[str, Any]]) -> None:
    """在 notebook 中展示提取结果对比

    Args:
        results: 提取结果列表
    """
    try:
        from IPython.display import display, HTML

        html = """
        <div style="max-height: 600px; overflow-y: auto;">
        """

        for i, result in enumerate(results):
            seed = result.get("seed", "unknown")
            extract = result.get("extract", {})
            duration = result.get("duration_ms", 0)
            error = result.get("error")

            if error:
                html += f"""
                <div style="border: 1px solid #f44; padding: 10px; margin: 5px 0; background: #fee;">
                    <h4 style="margin: 0 0 5px 0;">❌ {seed}</h4>
                    <p style="margin: 0; color: #f44;">Error: {error}</p>
                </div>
                """
            else:
                html += f"""
                <div style="border: 1px solid #4a4; padding: 10px; margin: 5px 0; background: #efe;">
                    <h4 style="margin: 0 0 5px 0;">✅ {seed}</h4>
                    <p style="margin: 0 0 5px 0; color: #666;">Duration: {duration:.0f}ms</p>
                    <pre style="background: #fff; padding: 5px; margin: 0;">{json.dumps(extract, indent=2, ensure_ascii=False)}</pre>
                </div>
                """

        html += """
        </div>
        """

        display(HTML(html))
    except ImportError:
        # 非 notebook 环境，打印 JSON
        for result in results:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 50)


def create_experiment_widget() -> None:
    """创建实验管理 widget（仅 Jupyter notebook）"""
    try:
        import ipywidgets as widgets
        from IPython.display import display

        # 创建 UI 组件
        name_input = widgets.Text(
            placeholder="Enter experiment name",
            description="Name:",
        )
        urls_input = widgets.Textarea(
            placeholder="Enter URLs (one per line)",
            description="URLs:",
            layout=widgets.Layout(width="500px", height="100px"),
        )
        run_button = widgets.Button(
            description="Run Experiment",
            button_style="success",
        )
        output = widgets.Output()

        def on_run_clicked(b):
            with output:
                output.clear_output()
                print(f"Running experiment: {name_input.value}")
                print(f"URLs: {urls_input.value}")

        run_button.on_click(on_run_clicked)

        display(name_input, urls_input, run_button, output)

    except ImportError:
        print("ipywidgets is required for widget support")
        print("Install with: pip install ipywidgets")
