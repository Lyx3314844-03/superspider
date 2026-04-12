from flask import Flask, jsonify, render_template_string
import redis
import json
import time

app = Flask(__name__)
r = redis.from_url("redis://localhost:6379", decode_responses=True)

# 统一键名
QUEUE_KEY = "spider:shared:queue"
VISITED_KEY = "spider:shared:visited"
STATS_KEY = "spider:shared:stats"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Language Spider Monitor</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: sans-serif; background: #f4f4f9; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #eee; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; color: #007bff; }
        canvas { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>爬虫框架互通监控面板</h1>
        <div class="stats-grid">
            <div class="stat-card"><div>总处理量</div><div id="total-processed" class="stat-value">0</div></div>
            <div class="stat-card"><div>成功数</div><div id="total-success" class="stat-value">0</div></div>
            <div class="stat-card"><div>失败数</div><div id="total-failed" class="stat-value">0</div></div>
            <div class="stat-card"><div>队列剩余</div><div id="queue-len" class="stat-value">0</div></div>
        </div>
        <canvas id="spiderChart" width="400" height="150"></canvas>
    </div>

    <script>
        const ctx = document.getElementById('spiderChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['JavaSpider', 'RustSpider', 'PySpider', 'GoSpider'],
                datasets: [{
                    label: '处理任务数',
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#f39c12', '#e74c3c', '#3498db', '#2ecc71']
                }]
            },
            options: { scales: { y: { beginAtZero: true } } }
        });

        function updateStats() {
            fetch('/api/stats')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('total-processed').innerText = data.processed || 0;
                    document.getElementById('total-success').innerText = data.success || 0;
                    document.getElementById('total-failed').innerText = data.failed || 0;
                    document.getElementById('queue-len').innerText = data.queue_len || 0;
                    
                    // 这里为了演示，我们假设 stats 里有各个语言的计数
                    // 实际代码中各框架写入时可以带上前缀，如 "java:success"
                    chart.data.datasets[0].data = [
                        data['java:processed'] || 0,
                        data['rust:processed'] || 0,
                        data['python:processed'] || 0,
                        data['go:processed'] || 0
                    ];
                    chart.update();
                });
        }

        setInterval(updateStats, 2000);
        updateStats();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def get_stats():
    try:
        stats = r.hgetall(STATS_KEY)
        stats['queue_len'] = r.zcard(QUEUE_KEY)
        stats['visited_len'] = r.scard(VISITED_KEY)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
