"""Write a conservative report from the dataset and recorded benchmark metadata."""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from s2st.languages import LITERATURE_BENCHMARKS


def generate_publication_report(output_dir: str = "artifacts/publication") -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rows = []
    for record in LITERATURE_BENCHMARKS.values():
        pair = f"{record['source_name']} ({record['source']}) → {record['target_name']} ({record['target']})"
        score = record.get("reported_asr_bleu")
        if score is not None:
            rows.append({
                "pair": pair,
                "dataset": "Literature reference; verify original citation",
                "score": f"{score} ASR-BLEU (reference only)",
            })
        else:
            rows.append({
                "pair": pair,
                "dataset": "Synthetic demo subset; not training data",
                "score": "Not measured",
            })

    markdown = [
        "# Speech-to-speech project data status",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}",
        "",
        "> The local checkout contains paired Yorùbá–English speech data from the IWSLT 2026 release. "
        "Audio waveforms, manifests, and review records are maintained in the data directory.",
        "",
        "## Benchmark records",
        "",
        "| Language pair | Data status | ASR-BLEU |",
        "|---|---|---|",
    ]
    markdown.extend(f"| {row['pair']} | {row['dataset']} | {row['score']} |" for row in rows)
    markdown.extend([
        "",
        "Any literature reference must be verified against its original publication before use.",
        "",
        "For the dataset layout and collection requirements, see `data/README.md` and `DATASETS.md`.",
        "",
    ])
    markdown_text = "\n".join(markdown)

    latex = r"""% Dataset status; demo data are not evaluation results.
\begin{table}[t]
\centering
\small
\begin{tabular}{lll}
\hline
Language pair & Data status & ASR-BLEU \\
\hline
"""
    for row in rows:
        latex += f"{row['pair']} & {row['dataset']} & {row['score']} \\" + "\n"
    latex += r"""\hline
\end{tabular}
\caption{Current benchmark metadata. Demo records are not model results.}
\end{table}
"""

    report_path = output_path / "PUBLICATION_REPORT.md"
    latex_path = output_path / "paper_tables.tex"
    report_path.write_text(markdown_text, encoding="utf-8")
    latex_path.write_text(latex, encoding="utf-8")
    return {
        "report_markdown": str(report_path),
        "latex_table": str(latex_path),
        "benchmarks": rows,
    }


if __name__ == "__main__":
    result = generate_publication_report()
    print(f"Dataset status report generated at {result['report_markdown']}")
