(function () {
  const API = '/api';
  let gameId = '';
  let pollTimer = null;
  const POLL_MS = 2500;

  const el = (id) => document.getElementById(id);
  const gameIdInput = el('gameId');
  const phaseStepper = el('phaseStepper');
  const trolleyBoard = el('trolleyBoard');
  const operatorName = el('operatorName');
  const majorityTokens = el('majorityTokens');
  const minorityTokens = el('minorityTokens');
  const trackMajority = el('trackMajority');
  const trackMinority = el('trackMinority');
  const resolutionText = el('resolutionText');
  const gameStatusEl = el('gameStatus');
  const roundPhaseEl = el('roundPhase');
  const roleAssignments = el('roleAssignments');
  const feedEl = el('feed');
  const dialogueEl = el('dialogue');
  const scoreboardEl = el('scoreboard');
  const coverageEl = el('coverage');

  function getGameId() {
    return (gameIdInput && gameIdInput.value.trim()) || gameId;
  }

  function setGameId(id) {
    gameId = id;
    if (gameIdInput) gameIdInput.value = id;
  }

  function initials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.slice(0, 2).toUpperCase();
  }

  function drawToken(parent, agent, role, opts) {
    const { x, y, argued, lost, survived } = opts || {};
    const cls = ['token-svg'];
    if (lost) cls.push('lost');
    if (survived) cls.push('survived');
    if (argued) cls.push('argued');
    const fill = role === 'operator' ? '#7c3aed' : role === 'majority' ? '#22c55e' : '#ef4444';
    const stroke = lost ? '#64748b' : argued ? '#fbbf24' : '#4a4a6a';
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', cls.join(' '));
    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', x);
    circle.setAttribute('cy', y);
    circle.setAttribute('r', 18);
    circle.setAttribute('fill', lost ? '#475569' : fill);
    circle.setAttribute('stroke', stroke);
    circle.setAttribute('stroke-width', 2);
    g.appendChild(circle);
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', x);
    text.setAttribute('y', y + 5);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', lost ? '#94a3b8' : '#fff');
    text.setAttribute('font-size', 9);
    text.textContent = initials(agent.display_name);
    g.appendChild(text);
    if (argued) {
      const bubble = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      bubble.setAttribute('cx', x + 14);
      bubble.setAttribute('cy', y - 14);
      bubble.setAttribute('r', 6);
      bubble.setAttribute('fill', '#fbbf24');
      bubble.setAttribute('stroke', '#fff');
      g.appendChild(bubble);
    }
    parent.appendChild(g);
  }

  function renderBoard(state) {
    if (!state || !trolleyBoard) return;
    const board = state.board || {};
    const phase = state.current_phase || '';

    // Phase stepper
    phaseStepper.querySelectorAll('.phase').forEach((span) => {
      span.classList.remove('active', 'done');
      const p = span.getAttribute('data-phase');
      const idx = ['phase_1', 'phase_2', 'phase_3', 'awaiting_decision', 'resolved'].indexOf(p);
      const currentIdx = ['phase_1', 'phase_2', 'phase_3', 'awaiting_decision', 'resolved'].indexOf(phase);
      if (idx < currentIdx) span.classList.add('done');
      else if (idx === currentIdx) span.classList.add('active');
    });

    // Operator
    if (state.operator) {
      operatorName.textContent = state.operator.display_name || 'Op';
    } else {
      operatorName.textContent = '—';
    }

    // Majority tokens (top track: y ~100)
    majorityTokens.innerHTML = '';
    const maj = state.majority_agents || [];
    const survivors = (board.survivors || []);
    const lost = (board.lost || []);
    maj.forEach((agent, i) => {
      const x = 320 + (i * 42);
      const y = 100;
      drawToken(majorityTokens, agent, 'majority', {
        x, y,
        argued: agent.argued_this_phase,
        lost: lost.includes(agent.id),
        survived: state.decision && survivors.includes(agent.id),
      });
    });

    // Minority tokens (bottom track: y ~240)
    minorityTokens.innerHTML = '';
    const min = state.minority_agents || [];
    min.forEach((agent, i) => {
      const x = 320 + (i * 42);
      const y = 240;
      drawToken(minorityTokens, agent, 'minority', {
        x, y,
        argued: agent.argued_this_phase,
        lost: lost.includes(agent.id),
        survived: state.decision && survivors.includes(agent.id),
      });
    });

    // Highlight chosen branch
    if (board.selected_branch === 'save_majority') {
      trackMajority.setAttribute('stroke', '#22c55e');
      trackMinority.setAttribute('stroke', '#64748b');
    } else if (board.selected_branch === 'save_minority') {
      trackMinority.setAttribute('stroke', '#ef4444');
      trackMajority.setAttribute('stroke', '#64748b');
    } else {
      trackMajority.setAttribute('stroke', '#4a4a6a');
      trackMinority.setAttribute('stroke', '#4a4a6a');
    }

    // Resolution text
    if (board.resolution_state && state.decision) {
      resolutionText.setAttribute('visibility', 'visible');
      resolutionText.textContent = 'Saved: ' + (state.decision === 'save_majority' ? 'Majority' : 'Minority');
    } else {
      resolutionText.setAttribute('visibility', 'hidden');
    }
  }

  function renderStatus(state) {
    gameStatusEl.textContent = 'Status: ' + (state ? state.status : '—');
    roundPhaseEl.textContent = state
      ? `Round ${state.current_round_number} · ${state.current_phase || '—'}`
      : '—';
  }

  function renderRoleAssignments(state) {
    if (!state) {
    roleAssignments.innerHTML = '—';
    return;
    }
    let html = '';
    if (state.operator) {
      html += '<p><strong>Operator:</strong> ' + escapeHtml(state.operator.display_name) + '</p>';
    }
    if ((state.majority_agents || []).length) {
      html += '<p><strong>Majority:</strong> ' + (state.majority_agents || []).map(a => escapeHtml(a.display_name)).join(', ') + '</p>';
    }
    if ((state.minority_agents || []).length) {
      html += '<p><strong>Minority:</strong> ' + (state.minority_agents || []).map(a => escapeHtml(a.display_name)).join(', ') + '</p>';
    }
    roleAssignments.innerHTML = html || '—';
  }

  function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function renderFeed(items) {
    const args = (items || []).filter((it) => it.type === 'argument');
    const events = (items || []).filter((it) => it.type === 'event');

    if (dialogueEl) {
      if (!args.length) {
        dialogueEl.innerHTML = '<p class="dialogue-empty">No arguments yet. Use <strong>Run fillers</strong> or have agents submit via API during debate phases.</p>';
      } else {
        dialogueEl.innerHTML = args.slice(0, 50).map((it) => {
          const name = escapeHtml(it.display_name || it.agent_id || 'Agent');
          const phase = it.phase ? 'Phase ' + it.phase.replace('phase_', '') : '';
          const text = escapeHtml(it.text || '');
          return '<div class="dialogue-line"><span class="dialogue-meta">' + name + (phase ? ' · ' + phase : '') + '</span><div class="dialogue-bubble">' + text + '</div></div>';
        }).join('');
      }
    }

    if (!events.length) {
      feedEl.innerHTML = '<div class="feed-item">No events yet.</div>';
      return;
    }
    feedEl.innerHTML = events.slice(0, 25).map((it) => {
      const p = it.payload || {};
      const short = p.phase ? 'Phase: ' + p.phase : (p.event_type || JSON.stringify(p).slice(0, 60));
      return '<div class="feed-item"><span class="feed-type">Event</span> ' + escapeHtml(short) + '</div>';
    }).join('');
  }

  function renderScoreboard(data) {
    if (!data || !data.scores) {
      scoreboardEl.innerHTML = '—';
      return;
    }
    scoreboardEl.innerHTML = data.scores.map((r) => `<div class="score-row"><span>${escapeHtml(r.display_name)}</span><strong>${r.score}</strong></div>`).join('');
  }

  function renderCoverage(data) {
    if (!data || !data.coverage) {
      coverageEl.innerHTML = '—';
      return;
    }
    coverageEl.innerHTML = data.coverage.map((c) => {
      const status = c.complete ? '<span class="done">✓</span>' : '<span class="pending">Op/Maj/Min</span>';
      return `<div class="coverage-row"><span>${escapeHtml(c.display_name)}</span> ${status}</div>`;
    }).join('');
  }

  async function fetchState() {
    const id = getGameId();
    if (!id) return null;
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/state');
      if (!r.ok) return null;
      return await r.json();
    } catch (e) {
      console.warn('State fetch failed', e);
      return null;
    }
  }

  async function fetchFeed() {
    const id = getGameId();
    if (!id) return [];
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/feed?limit=50');
      if (!r.ok) return [];
      const data = await r.json();
      return data.items || [];
    } catch (e) {
      return [];
    }
  }

  async function fetchScoreboard() {
    const id = getGameId();
    if (!id) return null;
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/scoreboard');
      if (!r.ok) return null;
      return await r.json();
    } catch (e) {
      return null;
    }
  }

  async function poll() {
    const state = await fetchState();
    renderStatus(state);
    renderRoleAssignments(state);
    renderBoard(state);
    const feed = await fetchFeed();
    renderFeed(feed);
    const score = await fetchScoreboard();
    renderScoreboard(score);
    renderCoverage(score);
  }

  function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    poll();
    pollTimer = setInterval(poll, POLL_MS);
  }

  async function createDemo() {
    try {
      const r = await fetch(API + '/demo/create', { method: 'POST' });
      const data = await r.json();
      setGameId(data.game_id);
      startPolling();
      alert('Demo game created. Click "Start game" to begin, or run the simulator.');
    } catch (e) {
      alert('Failed: ' + e.message);
    }
  }

  async function startGame() {
    const id = getGameId();
    if (!id) {
      alert('Load or create a game first');
      return;
    }
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/start', { method: 'POST' });
      if (!r.ok) {
        const err = await r.json();
        throw new Error(err.detail || r.statusText);
      }
      startPolling();
    } catch (e) {
      alert('Start failed: ' + e.message);
    }
  }

  async function loadGame() {
    const id = getGameId();
    if (!id) {
      alert('Enter a game ID');
      return;
    }
    setGameId(id);
    startPolling();
  }

  async function advanceGame() {
    const id = getGameId();
    if (!id) {
      alert('Load a game first');
      return;
    }
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'next_phase' }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.message || 'Advance failed');
      startPolling();
    } catch (e) {
      alert('Advance failed: ' + e.message);
    }
  }

  async function resolveRound() {
    const id = getGameId();
    if (!id) {
      alert('Load a game first');
      return;
    }
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/advance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'resolve_round' }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.message || 'Resolve failed');
      startPolling();
    } catch (e) {
      alert('Resolve failed: ' + e.message);
    }
  }

  async function addFiller() {
    const id = getGameId();
    if (!id) {
      alert('Load or create a game first');
      return;
    }
    const count = parseInt(el('fillerCount')?.value || '2', 10) || 2;
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/add-filler', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: Math.max(1, Math.min(5, count)) }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || data.message || 'Add filler failed');
      startPolling();
      alert('Added ' + (data.added?.length || 0) + ' filler agent(s). Start the game when ready.');
    } catch (e) {
      alert('Add filler failed: ' + e.message);
    }
  }

  async function tickFiller() {
    const id = getGameId();
    if (!id) return;
    try {
      const r = await fetch(API + '/games/' + encodeURIComponent(id) + '/tick-filler', { method: 'POST' });
      const data = await r.json();
      if (data.action) startPolling();
    } catch (_) {}
  }

  let autoTickInterval = null;
  function updateAutoTick() {
    const check = el('autoTickFiller');
    if (check?.checked) {
      if (!autoTickInterval) {
        autoTickInterval = setInterval(async () => {
          const id = getGameId();
          if (!id) return;
          const state = await fetchState();
          if (state && state.status !== 'game_completed' && state.status !== 'waiting_for_agents' && state.status !== 'ready_to_start') {
            await tickFiller();
          }
        }, 4000);
      }
    } else {
      if (autoTickInterval) {
        clearInterval(autoTickInterval);
        autoTickInterval = null;
      }
    }
  }

  el('btnCreateDemo').addEventListener('click', createDemo);
  el('btnStart').addEventListener('click', startGame);
  el('btnLoad').addEventListener('click', loadGame);
  el('btnAdvance').addEventListener('click', advanceGame);
  el('btnResolveRound').addEventListener('click', resolveRound);
  el('btnAddFiller').addEventListener('click', addFiller);
  el('btnTickFiller').addEventListener('click', () => { tickFiller().then(startPolling); });
  el('autoTickFiller').addEventListener('change', updateAutoTick);

  // Auto-load game_id from URL query (e.g. ?game_id=xxx)
  const params = new URLSearchParams(window.location.search);
  const urlGameId = params.get('game_id');
  if (urlGameId && gameIdInput) {
    setGameId(urlGameId.trim());
    startPolling();
  }
})();
