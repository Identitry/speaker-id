// Speaker-ID Web Interface
// Main application logic

// State Management
const state = {
    identifyAudio: null,
    enrollAudio: null,
    identifyRecorder: null,
    enrollRecorder: null,
    identifyMediaStream: null,
    enrollMediaStream: null,
    selectedSpeakers: new Set()
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeIdentifyTab();
    initializeEnrollTab();
    initializeManageTab();
    initializeSettingsTab();
    initializeAPITab();
    checkServerHealth();
});

// ===== Tab Management =====
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;

            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(targetTab).classList.add('active');

            // Load tab-specific data
            if (targetTab === 'manage') {
                loadSpeakers();
            } else if (targetTab === 'settings') {
                loadSettings();
            }
        });
    });
}

// ===== Server Health Check =====
async function checkServerHealth() {
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    try {
        const response = await fetch('/health');
        const data = await response.json();

        if (data.status === 'ok') {
            statusDot.classList.add('online');
            statusText.textContent = 'Online';
        } else {
            throw new Error('Unhealthy');
        }
    } catch (error) {
        statusDot.classList.add('offline');
        statusText.textContent = 'Offline';
    }
}

// ===== Identify Tab =====
function initializeIdentifyTab() {
    // File upload
    const fileInput = document.getElementById('identifyFileInput');
    const fileName = document.getElementById('identifyFileName');
    const identifyBtn = document.getElementById('identifyBtn');

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            state.identifyAudio = file;
            fileName.textContent = file.name;
            fileName.classList.add('has-file');
            identifyBtn.disabled = false;
        }
    });

    // Recording
    const recordBtn = document.getElementById('identifyRecordBtn');
    recordBtn.addEventListener('click', () => toggleRecording('identify'));

    // Threshold slider
    const threshold = document.getElementById('identifyThreshold');
    const thresholdValue = document.getElementById('thresholdValue');
    threshold.addEventListener('input', (e) => {
        thresholdValue.textContent = e.target.value;
    });

    // Identify button
    identifyBtn.addEventListener('click', identifySpeaker);
}

async function toggleRecording(tab) {
    const recordBtn = document.getElementById(`${tab}RecordBtn`);
    const statusDiv = document.getElementById(`${tab}RecordingStatus`);
    const playback = document.getElementById(`${tab}AudioPlayback`);
    const recorder = state[`${tab}Recorder`];

    if (!recorder || recorder.state === 'inactive') {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            state[`${tab}MediaStream`] = stream;

            // Try to use audio/wav if supported, otherwise use default
            const mimeType = MediaRecorder.isTypeSupported('audio/wav') ? 'audio/wav' :
                           MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';

            const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
            state[`${tab}Recorder`] = mediaRecorder;

            const audioChunks = [];

            mediaRecorder.addEventListener('dataavailable', (e) => {
                audioChunks.push(e.data);
            });

            mediaRecorder.addEventListener('stop', async () => {
                // Create blob from chunks
                const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
                const audioUrl = URL.createObjectURL(audioBlob);

                playback.src = audioUrl;
                playback.style.display = 'block';

                // Convert to WAV using AudioContext if not already WAV
                let finalBlob = audioBlob;
                if (!mediaRecorder.mimeType.includes('wav')) {
                    try {
                        finalBlob = await convertToWav(audioBlob);
                        statusDiv.textContent = 'Recording saved and converted to WAV.';
                    } catch (err) {
                        console.warn('WAV conversion failed, using original format:', err);
                        statusDiv.textContent = 'Recording saved (server will convert format).';
                    }
                } else {
                    statusDiv.textContent = 'Recording saved. You can play it back above.';
                }

                // Store for upload
                const file = new File([finalBlob], 'recording.wav', { type: 'audio/wav' });
                state[`${tab}Audio`] = file;

                // Enable submit button
                const submitBtn = document.getElementById(`${tab}Btn`);
                submitBtn.disabled = false;

                // Stop media stream
                stream.getTracks().forEach(track => track.stop());
            });

            mediaRecorder.start();

            recordBtn.classList.add('recording');
            recordBtn.innerHTML = `
                <svg class="record-icon" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12"></rect>
                </svg>
                <span>Stop Recording</span>
            `;
            statusDiv.textContent = 'Recording... Speak now';

        } catch (error) {
            showError(`${tab}Result`, 'Microphone access denied. Please allow microphone access in your browser settings.');
        }
    } else {
        // Stop recording
        state[`${tab}Recorder`].stop();

        recordBtn.classList.remove('recording');
        recordBtn.innerHTML = `
            <svg class="record-icon" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="10"></circle>
            </svg>
            <span>Start Recording</span>
        `;
    }
}

// Convert audio blob to WAV format using Web Audio API
async function convertToWav(audioBlob) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

    // Convert to WAV
    const wavBuffer = audioBufferToWav(audioBuffer);
    return new Blob([wavBuffer], { type: 'audio/wav' });
}

// Convert AudioBuffer to WAV format
function audioBufferToWav(buffer) {
    const length = buffer.length * buffer.numberOfChannels * 2;
    const arrayBuffer = new ArrayBuffer(44 + length);
    const view = new DataView(arrayBuffer);
    const channels = [];
    let offset = 0;
    let pos = 0;

    // Write WAV header
    const setUint16 = (data) => { view.setUint16(pos, data, true); pos += 2; };
    const setUint32 = (data) => { view.setUint32(pos, data, true); pos += 4; };

    // "RIFF" chunk descriptor
    setUint32(0x46464952); // "RIFF"
    setUint32(36 + length); // file length - 8
    setUint32(0x45564157); // "WAVE"

    // "fmt " sub-chunk
    setUint32(0x20746d66); // "fmt "
    setUint32(16); // SubChunk1Size (16 for PCM)
    setUint16(1); // AudioFormat (1 for PCM)
    setUint16(buffer.numberOfChannels); // NumChannels
    setUint32(buffer.sampleRate); // SampleRate
    setUint32(buffer.sampleRate * buffer.numberOfChannels * 2); // ByteRate
    setUint16(buffer.numberOfChannels * 2); // BlockAlign
    setUint16(16); // BitsPerSample

    // "data" sub-chunk
    setUint32(0x61746164); // "data"
    setUint32(length); // SubChunk2Size

    // Write interleaved audio data
    for (let i = 0; i < buffer.numberOfChannels; i++) {
        channels.push(buffer.getChannelData(i));
    }

    while (pos < arrayBuffer.byteLength) {
        for (let i = 0; i < buffer.numberOfChannels; i++) {
            let sample = Math.max(-1, Math.min(1, channels[i][offset]));
            sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
            view.setInt16(pos, sample, true);
            pos += 2;
        }
        offset++;
    }

    return arrayBuffer;
}

async function identifySpeaker() {
    const threshold = document.getElementById('identifyThreshold').value;
    const resultDiv = document.getElementById('identifyResult');
    const identifyBtn = document.getElementById('identifyBtn');

    if (!state.identifyAudio) {
        showError('identifyResult', 'Please record or upload an audio file first.');
        return;
    }

    identifyBtn.disabled = true;
    identifyBtn.textContent = 'Identifying...';

    const formData = new FormData();
    formData.append('file', state.identifyAudio);

    try {
        const response = await fetch(`/api/identify?threshold=${threshold}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            if (data.speaker === 'unknown') {
                showWarning('identifyResult', 'Speaker Unknown',
                    `No match found above confidence threshold of ${threshold}. Try lowering the threshold or enrolling this speaker.`,
                    data.topN || []);
            } else {
                showSuccess('identifyResult', `Speaker: ${data.speaker}`,
                    `Identified with ${(data.confidence * 100).toFixed(1)}% confidence.`,
                    data.confidence,
                    data.topN || []);
            }
        } else {
            showError('identifyResult', data.detail || 'Identification failed');
        }
    } catch (error) {
        showError('identifyResult', 'Network error. Please check if the server is running.');
    } finally {
        identifyBtn.disabled = false;
        identifyBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
            </svg>
            Identify Speaker
        `;
    }
}

// ===== Enroll Tab =====
function initializeEnrollTab() {
    // File upload
    const fileInput = document.getElementById('enrollFileInput');
    const fileName = document.getElementById('enrollFileName');
    const enrollBtn = document.getElementById('enrollBtn');
    const nameInput = document.getElementById('enrollName');

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            state.enrollAudio = file;
            fileName.textContent = file.name;
            fileName.classList.add('has-file');
            updateEnrollButton();
        }
    });

    // Recording
    const recordBtn = document.getElementById('enrollRecordBtn');
    recordBtn.addEventListener('click', () => toggleRecording('enroll'));

    // Name input
    nameInput.addEventListener('input', updateEnrollButton);

    // Enroll button
    enrollBtn.addEventListener('click', enrollSpeaker);
}

function updateEnrollButton() {
    const enrollBtn = document.getElementById('enrollBtn');
    const nameInput = document.getElementById('enrollName');
    enrollBtn.disabled = !(nameInput.value.trim() && state.enrollAudio);
}

async function enrollSpeaker() {
    const name = document.getElementById('enrollName').value.trim();
    const resultDiv = document.getElementById('enrollResult');
    const enrollBtn = document.getElementById('enrollBtn');

    if (!name) {
        showError('enrollResult', 'Please enter a speaker name.');
        return;
    }

    if (!state.enrollAudio) {
        showError('enrollResult', 'Please record or upload an audio file first.');
        return;
    }

    enrollBtn.disabled = true;
    enrollBtn.textContent = 'Enrolling...';

    const formData = new FormData();
    formData.append('file', state.enrollAudio);

    try {
        const response = await fetch(`/api/enroll?name=${encodeURIComponent(name)}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess('enrollResult', 'Enrollment Successful',
                `${data.name} has been enrolled with ${data.samples} sample(s). For best results, enroll 3-5 samples per person.`);

            // Reset form
            document.getElementById('enrollName').value = '';
            document.getElementById('enrollFileName').textContent = '';
            document.getElementById('enrollAudioPlayback').style.display = 'none';
            state.enrollAudio = null;
        } else {
            showError('enrollResult', data.detail || 'Enrollment failed');
        }
    } catch (error) {
        showError('enrollResult', 'Network error. Please check if the server is running.');
    } finally {
        updateEnrollButton();
        enrollBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"></path>
                <circle cx="8.5" cy="7" r="4"></circle>
                <line x1="20" y1="8" x2="20" y2="14"></line>
                <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Enroll Speaker
        `;
    }
}

// ===== Manage Tab =====
function initializeManageTab() {
    document.getElementById('refreshSpeakers').addEventListener('click', loadSpeakers);
    document.getElementById('deleteSelected').addEventListener('click', deleteSelectedSpeakers);
}

async function loadSpeakers() {
    const speakersList = document.getElementById('speakersList');
    speakersList.innerHTML = '<div class="loading">Loading speakers...</div>';

    try {
        const response = await fetch('/api/profiles');
        const data = await response.json();

        if (response.ok && data.profiles && data.profiles.length > 0) {
            speakersList.innerHTML = data.profiles.map(name => `
                <div class="speaker-item">
                    <input type="checkbox" class="speaker-checkbox" data-name="${name}">
                    <div class="speaker-avatar">${name.charAt(0).toUpperCase()}</div>
                    <div class="speaker-info">
                        <div class="speaker-name">${name}</div>
                        <div class="speaker-meta">Enrolled speaker</div>
                    </div>
                    <div class="speaker-actions">
                        <button class="icon-button danger" onclick="deleteSpeaker('${name}')" title="Delete">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            `).join('');

            // Add checkbox listeners
            document.querySelectorAll('.speaker-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', (e) => {
                    if (e.target.checked) {
                        state.selectedSpeakers.add(e.target.dataset.name);
                    } else {
                        state.selectedSpeakers.delete(e.target.dataset.name);
                    }
                    document.getElementById('deleteSelected').disabled = state.selectedSpeakers.size === 0;
                });
            });
        } else {
            speakersList.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M23 21v-2a4 4 0 00-3-3.87m-4-12a4 4 0 010 7.75"></path>
                    </svg>
                    <h3>No Speakers Enrolled</h3>
                    <p>Go to the Enroll tab to add speakers to the system.</p>
                </div>
            `;
        }
    } catch (error) {
        speakersList.innerHTML = '<div class="loading">Failed to load speakers. Server may be offline.</div>';
    }
}

async function deleteSpeaker(name) {
    if (!confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/reset?name=${encodeURIComponent(name)}`, {
            method: 'POST'
        });

        if (response.ok) {
            loadSpeakers();
        } else {
            alert('Failed to delete speaker');
        }
    } catch (error) {
        alert('Network error');
    }
}

async function deleteSelectedSpeakers() {
    if (state.selectedSpeakers.size === 0) return;

    const count = state.selectedSpeakers.size;
    if (!confirm(`Are you sure you want to delete ${count} speaker(s)? This action cannot be undone.`)) {
        return;
    }

    const promises = Array.from(state.selectedSpeakers).map(name =>
        fetch(`/api/reset?name=${encodeURIComponent(name)}`, { method: 'POST' })
    );

    try {
        await Promise.all(promises);
        state.selectedSpeakers.clear();
        loadSpeakers();
    } catch (error) {
        alert('Failed to delete some speakers');
    }
}

// ===== Settings Tab =====
function initializeSettingsTab() {
    document.getElementById('rebuildCentroids').addEventListener('click', rebuildCentroids);
    document.getElementById('resetDatabase').addEventListener('click', resetDatabase);
}

async function loadSettings() {
    try {
        const [configRes, profilesRes] = await Promise.all([
            fetch('/api/config'),
            fetch('/api/profiles')
        ]);

        if (configRes.ok) {
            const config = await configRes.json();
            document.getElementById('settingsStatus').textContent = 'Online';
            document.getElementById('settingsStatus').style.color = 'var(--success)';
            document.getElementById('settingsModel').textContent = config.model || 'Resemblyzer';
            document.getElementById('settingsEmbeddingDim').textContent = config.embedding_dim || '256';
            document.getElementById('settingsSampleRate').textContent = `${config.sample_rate || '16000'} Hz`;
            document.getElementById('settingsThreshold').textContent = config.default_threshold || '0.82';
            document.getElementById('settingsVersion').textContent = config.version || '1.0.0';
        }

        if (profilesRes.ok) {
            const profiles = await profilesRes.json();
            document.getElementById('settingsSpeakerCount').textContent = profiles.profiles?.length || 0;
        }
    } catch (error) {
        document.getElementById('settingsStatus').textContent = 'Offline';
        document.getElementById('settingsStatus').style.color = 'var(--error)';
    }
}

async function rebuildCentroids() {
    if (!confirm('Rebuild all speaker centroids? This may take a moment.')) {
        return;
    }

    try {
        const response = await fetch('/api/rebuild_centroids', { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            alert(`Successfully rebuilt centroids for ${data.speakers_updated || 0} speaker(s)`);
        } else {
            alert('Failed to rebuild centroids');
        }
    } catch (error) {
        alert('Network error');
    }
}

async function resetDatabase() {
    if (!confirm('⚠️ DELETE ALL DATA? This will permanently remove all enrolled speakers. This action CANNOT be undone!')) {
        return;
    }

    if (!confirm('Are you absolutely sure? Type "DELETE" in the next prompt to confirm.')) {
        return;
    }

    const confirmation = prompt('Type DELETE to confirm:');
    if (confirmation !== 'DELETE') {
        alert('Reset cancelled');
        return;
    }

    try {
        const response = await fetch('/api/reset?drop_all=true', { method: 'POST' });

        if (response.ok) {
            alert('All data has been deleted');
            loadSettings();
            loadSpeakers();
        } else {
            alert('Failed to reset database');
        }
    } catch (error) {
        alert('Network error');
    }
}

// ===== API Tab =====
function initializeAPITab() {
    document.querySelectorAll('.copy-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const codeId = e.target.dataset.copy;
            const code = document.getElementById(codeId);
            navigator.clipboard.writeText(code.textContent);

            const originalText = e.target.textContent;
            e.target.textContent = 'Copied!';
            setTimeout(() => {
                e.target.textContent = originalText;
            }, 2000);
        });
    });
}

// ===== UI Helper Functions =====
function showSuccess(elementId, title, message, confidence = null, topMatches = []) {
    const element = document.getElementById(elementId);

    let html = `
        <div class="result-header">
            <svg class="result-icon" viewBox="0 0 24 24" fill="none" stroke="var(--success)">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
            <h3>${title}</h3>
        </div>
        <div class="result-content">
            <p>${message}</p>
    `;

    if (confidence !== null) {
        html += `
            <div class="confidence-bar">
                <div class="confidence-label">
                    <span>Confidence</span>
                    <span>${(confidence * 100).toFixed(1)}%</span>
                </div>
                <div class="confidence-track">
                    <div class="confidence-fill" style="width: ${confidence * 100}%"></div>
                </div>
            </div>
        `;
    }

    if (topMatches.length > 0) {
        html += `
            <div class="top-matches">
                <h4>Top Matches</h4>
                ${topMatches.map(match => `
                    <div class="match-item">
                        <span class="match-name">${match.name}</span>
                        <span class="match-score">${(match.score * 100).toFixed(1)}%</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    html += '</div>';

    element.innerHTML = html;
    element.className = 'result-panel success';
    element.style.display = 'block';
}

function showWarning(elementId, title, message, topMatches = []) {
    const element = document.getElementById(elementId);

    let html = `
        <div class="result-header">
            <svg class="result-icon" viewBox="0 0 24 24" fill="none" stroke="var(--warning)">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            <h3>${title}</h3>
        </div>
        <div class="result-content">
            <p>${message}</p>
    `;

    if (topMatches.length > 0) {
        html += `
            <div class="top-matches">
                <h4>Closest Matches (below threshold)</h4>
                ${topMatches.slice(0, 3).map(match => `
                    <div class="match-item">
                        <span class="match-name">${match.name}</span>
                        <span class="match-score">${(match.score * 100).toFixed(1)}%</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    html += '</div>';

    element.innerHTML = html;
    element.className = 'result-panel warning';
    element.style.display = 'block';
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);

    element.innerHTML = `
        <div class="result-header">
            <svg class="result-icon" viewBox="0 0 24 24" fill="none" stroke="var(--error)">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <h3>Error</h3>
        </div>
        <div class="result-content">
            <p>${message}</p>
        </div>
    `;

    element.className = 'result-panel error';
    element.style.display = 'block';
}
