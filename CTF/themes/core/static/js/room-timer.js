/**
 * Teck-Vision — Room countdown timer & VM control helpers
 * Used on /rooms/<slug> detail pages.
 */

class RoomTimer {
  /**
   * @param {string|number} expiresAt  ISO date string or Unix ms timestamp
   * @param {string}        containerId  ID of the DOM element to update
   * @param {Function}      [onExpire]   Callback fired when the timer hits 0
   */
  constructor(expiresAt, containerId, onExpire) {
    this.expires   = expiresAt instanceof Date ? expiresAt : new Date(expiresAt);
    this.container = document.getElementById(containerId);
    this.onExpire  = typeof onExpire === "function" ? onExpire : function () {};
    this._interval = null;

    if (!this.container) {
      console.warn("[RoomTimer] Container #" + containerId + " not found");
      return;
    }
    this._tick();
    this._interval = setInterval(() => this._tick(), 1000);
  }

  _remaining() {
    return Math.max(0, this.expires - Date.now());
  }

  _tick() {
    const ms   = this._remaining();
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    this.container.textContent = String(mins).padStart(2, "0") + ":" + String(secs).padStart(2, "0");

    /* Update a progress bar if present (data-timer-bar="<containerId>") */
    const bar = document.querySelector(`[data-timer-bar="${this.container.id}"]`);
    if (bar && bar._timerTotal) {
      const pct = Math.round((ms / bar._timerTotal) * 100);
      bar.style.width = pct + "%";
    }

    if (ms === 0) {
      clearInterval(this._interval);
      this._interval = null;
      this.onExpire();
    }
  }

  /** Stop the timer without triggering onExpire */
  stop() {
    clearInterval(this._interval);
    this._interval = null;
    if (this.container) this.container.textContent = "--:--";
  }

  /** Restart from a new expiry date */
  restart(newExpiresAt) {
    clearInterval(this._interval);
    this.expires   = newExpiresAt instanceof Date ? newExpiresAt : new Date(newExpiresAt);
    this._tick();
    this._interval = setInterval(() => this._tick(), 1000);
  }
}


/**
 * startRoomMachine — POST to the room-instances start API and update UI.
 *
 * @param {string}   roomSlug    e.g. "web-security-challenge"
 * @param {string}   csrfToken   CSRF nonce from window.init.csrfNonce
 * @param {Function} onSuccess   Called with (instanceData) when machine starts
 * @param {Function} [onError]   Called with (errorMsg) on failure
 */
function startRoomMachine(roomSlug, csrfToken, onSuccess, onError) {
  return fetch("/api/room-instances/start/" + roomSlug, {
    method:  "POST",
    headers: {
      "Content-Type": "application/json",
      "CSRF-Token":   csrfToken,
    },
  })
  .then(r => r.json())
  .then(data => {
    if (data.success !== false) {
      if (typeof onSuccess === "function") onSuccess(data);
    } else {
      if (typeof onError === "function") onError(data.message || "Failed to start machine");
    }
    return data;
  })
  .catch(err => {
    if (typeof onError === "function") onError(String(err));
    throw err;
  });
}


/**
 * terminateRoomMachine — POST to the room-instances terminate API.
 */
function terminateRoomMachine(roomSlug, csrfToken) {
  return fetch("/api/room-instances/terminate/" + roomSlug, {
    method:  "POST",
    headers: {
      "Content-Type": "application/json",
      "CSRF-Token":   csrfToken,
    },
  }).then(r => r.json());
}


/**
 * submitFlag — POST a flag to the challenge attempt API.
 *
 * @param {number}   challengeId
 * @param {string}   flag
 * @param {string}   csrfToken
 * @returns {Promise<{success:boolean, message:string, points?:number}>}
 */
function submitFlag(challengeId, flag, csrfToken) {
  return fetch("/api/challenges/" + challengeId + "/attempt", {
    method:  "POST",
    headers: {
      "Content-Type": "application/json",
      "CSRF-Token":   csrfToken,
    },
    body: JSON.stringify({ flag: (flag || "").trim() }),
  }).then(r => r.json());
}
