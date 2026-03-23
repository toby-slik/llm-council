export function generateMarkdownExport(messages) {
  let markdown = "# LLM Council - Creative Effectiveness Evaluation\n\n";
  const dateStr = new Date().toLocaleString();
  markdown += `*Exported on: ${dateStr}*\n\n---\n\n`;

  messages.forEach((msg) => {
    // Skip loading or internal messages if needed, here we export all relevant ones
    if (msg.type === "loading" || msg.type === "error") return;

    markdown += `### **${msg.role === "bot" ? "LLM Council AI" : "User"}**\n\n`;

    if (msg.content) {
      markdown += `${msg.content}\n\n`;
    }

    if (msg.type === "evaluation_results" && msg.extra?.results) {
      markdown += `## Evaluation Results\n\n`;

      msg.extra.results.forEach((r) => {
        markdown += `### Platform: ${r.platform}\n\n`;

        const {
          final_report,
          final_effectiveness_index,
          role_evaluations,
          hard_gate_failed,
          failed_hard_gate_role,
        } = r.result || {};

        if (final_report) {
          markdown += `#### Final Report\n\n`;
          markdown += `- **Verdict:** ${final_report.verdict}\n`;
          markdown += `- **Effectiveness Index:** ${final_effectiveness_index ? final_effectiveness_index.toFixed(1) : "N/A"}\n`;
          markdown += `- **Confidence Level:** ${final_report.confidence_level}\n`;
          markdown += `- **Predicted Commercial Role:** ${final_report.predicted_commercial_role}\n\n`;

          if (hard_gate_failed) {
            markdown += `**⛔ HARD GATE FAILED:** Evaluation stopped early due to failure in: ${failed_hard_gate_role}\n\n`;
          }

          markdown += `**Top Strengths:**\n`;
          if (
            final_report.top_strengths &&
            final_report.top_strengths.length > 0
          ) {
            final_report.top_strengths.forEach((s) => {
              markdown += `- ${s}\n`;
            });
          } else {
            markdown += `- None listed\n`;
          }
          markdown += `\n`;

          markdown += `**Top Risks:**\n`;
          if (final_report.top_risks && final_report.top_risks.length > 0) {
            final_report.top_risks.forEach((risk) => {
              markdown += `- ${risk}\n`;
            });
          } else {
            markdown += `- None listed\n`;
          }
          markdown += `\n`;

          if (final_report.revision_guidance) {
            markdown += `**Revision Guidance:**\n${final_report.revision_guidance}\n\n`;
          }
        }

        if (role_evaluations && role_evaluations.length > 0) {
          markdown += `#### Role Evaluations Summary\n\n`;
          markdown += `| Role | Result | Score | Confidence | Hard Gate |\n`;
          markdown += `|------|--------|-------|------------|-----------|\n`;

          role_evaluations.forEach((role) => {
            const scoreStr =
              role.score !== null ? role.score.toFixed(1) : "N/A";
            const confStr =
              role.confidence !== null
                ? `${(role.confidence * 100).toFixed(0)}%`
                : "N/A";
            markdown += `| ${role.role_name} | ${role.result} | ${scoreStr} | ${confStr} | ${role.is_hard_gate ? "Yes" : "No"} |\n`;
          });
          markdown += `\n`;

          markdown += `#### Detailed Role Analysis\n\n`;
          role_evaluations.forEach((role) => {
            markdown += `**${role.role_name}** - ${role.result}\n\n`;
            markdown += `*Justification:*\n${role.justification}\n\n`;

            if (role.layer_scores && role.layer_scores.length > 0) {
              markdown += `*Layer Scores:*\n\n`;
              role.layer_scores.forEach((layer) => {
                markdown += `- **Layer ${layer.layer_id}: ${layer.layer_name}** - ${layer.verdict}\n`;
                if (layer.fail_conditions && layer.fail_conditions.length > 0) {
                  layer.fail_conditions.forEach((fc) => {
                    markdown += `  - ⚠ ${fc}\n`;
                  });
                }
              });
              markdown += `\n`;
            }
            markdown += `---\n\n`;
          });
        }
      });
    }

    markdown += `\n---\n\n`;
  });

  return markdown;
}

function formatMarkdown(text) {
  if (!text) return "";

  // Replace literal '\n' strings with actual newlines first
  let formatted = text.replace(/\\n/g, "\n");

  // Bold
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Headers
  formatted = formatted.replace(/^### (.*$)/gim, "<h3>$1</h3>");
  formatted = formatted.replace(/^## (.*$)/gim, "<h2>$1</h2>");
  formatted = formatted.replace(/^# (.*$)/gim, "<h1>$1</h1>");

  // Tables
  const lines = formatted.split("\n");
  const result = [];
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();

    if (line.startsWith("|") && line.endsWith("|")) {
      if (!inTable) {
        inTable = true;
        result.push('<div style="overflow-x: auto; margin: 15px 0;"><table>');
      }

      // Skip separator rows like |---|---|
      if (line.replace(/[\s|:\-]/g, "") === "") {
        continue;
      }

      const cells = line.substring(1, line.length - 1).split("|");
      result.push("<tr>");

      // If it's the first line in the table block, treat as header
      const isHeader =
        (result[result.length - 2] &&
          result[result.length - 2].includes("<table>")) ||
        (result[result.length - 2] &&
          result[result.length - 2].includes("Overflow"));
      // wait, let's just use strict logic...

      cells.forEach((cell) => {
        const trimmed = cell.trim();
        // A simple way to check header: if it's the very first row inside the table
        if (
          result.length > 0 &&
          result[result.length - 2] ===
            '<div style="overflow-x: auto; margin: 15px 0;"><table>'
        ) {
          result.push(`<th>${trimmed}</th>`);
        } else {
          result.push(`<td>${trimmed}</td>`);
        }
      });
      result.push("</tr>");
    } else {
      if (inTable) {
        inTable = false;
        result.push("</table></div><br>");
      }
      result.push(line === "" ? "<br>" : `${line}<br>`);
    }
  }

  if (inTable) {
    result.push("</table></div>");
  }

  return result.join("\n");
}

export function generateHTMLExport(messages) {
  const dateStr = new Date().toLocaleString();

  let html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Council Evaluation Report</title>
    <style>
        :root {
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-red: #f85149;
            --accent-yellow: #d29922;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            margin: 0;
            padding: 40px 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 40px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 20px;
        }
        h1 { margin: 0; color: white; }
        .export-meta { color: var(--text-secondary); font-size: 0.9em; margin-top: 5px; }
        
        .chat-bubble {
            margin-bottom: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            background-color: var(--card-bg);
        }
        .chat-bubble.bot { border-left: 4px solid var(--accent-blue); }
        .chat-bubble.user { border-left: 4px solid var(--text-secondary); }
        .bubble-role { font-weight: bold; font-size: 0.8em; text-transform: uppercase; color: var(--accent-blue); margin-bottom: 8px; }
        .user .bubble-role { color: var(--text-secondary); }

        .evaluation-section {
            margin-top: 40px;
            padding: 30px;
            background: #1c2128;
            border-radius: 12px;
            border: 1px solid var(--accent-blue);
        }
        .platform-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 15px;
            margin-bottom: 25px;
        }
        .fei-badge {
            background: var(--accent-blue);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
        }

        .report-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        .report-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .report-card.strengths { border-top: 3px solid var(--accent-green); }
        .report-card.risks { border-top: 3px solid var(--accent-red); }
        h3, h4 { margin-top: 0; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
        }
        th, td {
            text-align: left;
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
        }
        th { background: #21262d; color: var(--text-secondary); font-size: 0.85em; }
        .verdict-TAG {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .verdict-recommend { background: rgba(63, 185, 80, 0.2); color: var(--accent-green); }
        .verdict-revise { background: rgba(210, 153, 34, 0.2); color: var(--accent-yellow); }
        .verdict-fail { background: rgba(248, 81, 73, 0.2); color: var(--accent-red); }

        .role-detail {
            background: var(--card-bg);
            margin-top: 15px;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        .justification { font-style: italic; color: var(--text-secondary); margin-bottom: 15px; }
        .layer-item { margin-bottom: 8px; font-size: 0.9em; padding-left: 10px; border-left: 2px solid var(--border-color); }
        .layer-fail { color: var(--accent-red); margin-left: 20px; font-size: 0.85em; }

        @media print {
            body { background: white; color: black; padding: 0; }
            .evaluation-section { page-break-before: always; border-color: #ddd; }
            .chat-bubble, .report-card { border-color: #ddd; background: white; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Creative Effectiveness Report</h1>
            <div class="export-meta">Generated on ${dateStr}</div>
        </header>

        <section class="chat-history">
            <h2>Conversation History</h2>`;

  messages.forEach((msg) => {
    if (msg.type === "loading" || msg.type === "error") return;

    html += `
            <div class="chat-bubble ${msg.role}">
                <div class="bubble-role">${msg.role === "bot" ? "LLM Council AI" : "User"}</div>
                <div class="bubble-content">${formatMarkdown(msg.content)}</div>
            </div>`;

    if (msg.type === "evaluation_results" && msg.extra?.results) {
      msg.extra.results.forEach((r) => {
        const {
          final_report,
          final_effectiveness_index,
          role_evaluations,
          hard_gate_failed,
          failed_hard_gate_role,
        } = r.result || {};

        html += `
            <div class="evaluation-section">
                <div class="platform-header">
                    <h2>Target Platform: ${r.platform}</h2>
                    <div class="fei-badge">FEI: ${final_effectiveness_index ? final_effectiveness_index.toFixed(1) : "N/A"}</div>
                </div>

                <div class="verdict-section" style="margin-bottom: 25px;">
                    <span class="verdict-TAG ${final_report?.verdict?.includes("REVISE") ? "verdict-revise" : final_report?.verdict?.includes("RECOMMEND") ? "verdict-recommend" : "verdict-fail"}">
                        ${final_report?.verdict || "N/A"}
                    </span>
                    <span style="color: var(--text-secondary); margin-left: 15px;">Confidence: ${final_report?.confidence_level || "N/A"}</span>
                </div>

                <div class="report-grid">
                    <div class="report-card strengths">
                        <h4>Top Strengths</h4>
                        <ul>
                            ${final_report?.top_strengths?.map((s) => `<li>${s}</li>`).join("") || "<li>None</li>"}
                        </ul>
                    </div>
                    <div class="report-card risks">
                        <h4>Top Risks</h4>
                        <ul>
                            ${final_report?.top_risks?.map((risk) => `<li>${risk}</li>`).join("") || "<li>None</li>"}
                        </ul>
                    </div>
                </div>

                ${
                  final_report?.revision_guidance
                    ? `<div class="report-card" style="margin-bottom: 30px;">
                    <h4>Revision Guidance</h4>
                    <p>${final_report.revision_guidance}</p>
                </div>`
                    : ""
                }

                <h3>LLM Council Deliberation</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Role</th>
                            <th>Result</th>
                            <th>Score</th>
                            <th>Conf.</th>
                            <th>Gate</th>
                        </tr>
                    </thead>
                    <tbody>`;

        role_evaluations?.forEach((role) => {
          html += `
                        <tr>
                            <td><strong>${role.role_name}</strong></td>
                            <td><span class="verdict-TAG ${role.result === "PASS" ? "verdict-recommend" : "verdict-fail"}">${role.result}</span></td>
                            <td>${role.score != null ? role.score.toFixed(1) : "N/A"}</td>
                            <td>${role.confidence != null ? (role.confidence * 100).toFixed(0) + "%" : "N/A"}</td>
                            <td>${role.is_hard_gate ? "⚠️" : "-"}</td>
                        </tr>`;
        });

        html += `
                    </tbody>
                </table>

                <h4>Detailed Analysis per Role</h4>`;

        role_evaluations?.forEach((role) => {
          html += `
                <div class="role-detail">
                    <div style="font-weight: bold; margin-bottom: 5px;">${role.role_name}</div>
                    <div class="justification">${role.justification}</div>
                    ${
                      role.layer_scores
                        ?.map(
                          (layer) => `
                        <div class="layer-item">
                            ${layer.layer_name}: <strong>${layer.verdict}</strong>
                            ${layer.fail_conditions?.map((fc) => `<div class="layer-fail">⚠ ${fc}</div>`).join("") || ""}
                        </div>
                    `,
                        )
                        .join("") || ""
                    }
                </div>`;
        });

        html += `</div>`;
      });
    }
  });

  html += `
        </section>
    </div>
</body>
</html>`;

  return html;
}
