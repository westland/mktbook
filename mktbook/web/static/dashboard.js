// MktBook WebSocket client for live dashboard updates

(function() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${location.host}/ws`;
    let ws = null;
    let reconnectDelay = 1000;

    function connect() {
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('MktBook WS connected');
            reconnectDelay = 1000;
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleEvent(data);
        };

        ws.onclose = function() {
            console.log('MktBook WS disconnected, reconnecting in', reconnectDelay, 'ms');
            setTimeout(connect, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 2, 30000);
        };

        ws.onerror = function(err) {
            console.error('MktBook WS error', err);
        };
    }

    function handleEvent(data) {
        const feed = document.getElementById('activity-feed');
        if (!feed) return;

        if (data.type === 'message') {
            const item = document.createElement('div');
            item.className = 'feed-item';
            item.innerHTML = `<strong>${escapeHtml(data.bot)}</strong>: ${escapeHtml(data.content.substring(0, 100))}` +
                `<small>${data.conversation_type} - just now</small>`;
            feed.insertBefore(item, feed.firstChild);

            // Keep feed manageable
            while (feed.children.length > 50) {
                feed.removeChild(feed.lastChild);
            }
        }

        if (data.type === 'conversation_start') {
            const item = document.createElement('div');
            item.className = 'feed-item';
            item.innerHTML = `<em>Conversation started: ${escapeHtml(data.initiator)} &harr; ${escapeHtml(data.responder)}</em>` +
                `<small>just now</small>`;
            feed.insertBefore(item, feed.firstChild);
        }

        if (data.type === 'grading_complete') {
            const item = document.createElement('div');
            item.className = 'feed-item';
            item.innerHTML = `<em>Grading run ${escapeHtml(data.run_id)} complete (${data.count} bots)</em>` +
                `<small>just now</small>`;
            feed.insertBefore(item, feed.firstChild);
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Only connect if we're on a page that might benefit
    if (document.getElementById('activity-feed') || document.getElementById('message-table-body')) {
        connect();
    }
})();
