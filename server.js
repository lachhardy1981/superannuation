'use strict';

const express    = require('express');
const path       = require('path');
const { execFile } = require('child_process');

const app  = express();
const PORT = process.env.PORT || 3000;

// 15-minute cache (matches Yahoo Finance delayed-quote window)
const cache   = {};
const CACHE_TTL = 15 * 60 * 1000;

app.use(express.static(path.join(__dirname)));

const PYTHON     = '/usr/bin/python3';
const PY_SCRIPT  = path.join(__dirname, 'fetch_sp500.py');

function runPython(range, interval) {
    return new Promise((resolve, reject) => {
        execFile(PYTHON, [PY_SCRIPT, range, interval], { timeout: 30000 }, (err, stdout, stderr) => {
            if (err) return reject(new Error(stderr || err.message));
            try { resolve(JSON.parse(stdout)); }
            catch (e) { reject(new Error('Failed to parse Python output: ' + stdout.slice(0, 200))); }
        });
    });
}

async function fetchSP500(range, interval) {
    const key = `${range}:${interval}`;
    if (cache[key] && Date.now() - cache[key].ts < CACHE_TTL) {
        return cache[key].data;
    }
    const data = await runPython(range, interval);
    cache[key] = { data, ts: Date.now() };
    return data;
}

const VALID_RANGES    = new Set(['1mo', '3mo', '6mo', '1y', '2y', '5y']);
const VALID_INTERVALS = new Set(['1d', '1wk']);

app.get('/api/sp500', async (req, res) => {
    const range    = req.query.range    || '1y';
    const interval = req.query.interval || '1d';

    if (!VALID_RANGES.has(range))       return res.status(400).json({ error: 'Invalid range' });
    if (!VALID_INTERVALS.has(interval)) return res.status(400).json({ error: 'Invalid interval' });

    try {
        res.json(await fetchSP500(range, interval));
    } catch (err) {
        console.error('[sp500]', err.message);
        res.status(500).json({ error: err.message });
    }
});

app.listen(PORT, () => {
    console.log(`\n  S&P 500 Technical Analysis`);
    console.log(`  ──────────────────────────────────────`);
    console.log(`  Dashboard  →  http://localhost:${PORT}/`);
    console.log(`  SP500 Chart→  http://localhost:${PORT}/sp500.html\n`);
});
