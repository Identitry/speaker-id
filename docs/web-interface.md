# Web Interface Guide

Modern, user-friendly web interface for Speaker-ID with dark blue/violet theme.

---

## Overview

The web interface provides a complete graphical interface for all Speaker-ID features:
- ✅ Speaker identification with adjustable threshold
- ✅ Speaker enrollment with multiple samples
- ✅ Speaker management (view, delete)
- ✅ System settings and configuration
- ✅ API documentation and examples

**Access**: http://localhost:8080

---

## Features

### 1. Identify Tab

Identify who is speaking from an audio sample.

**Features**:
- **Record Audio**: Click to record directly from your microphone
- **Upload File**: Upload pre-recorded WAV, MP3, or FLAC files
- **Adjustable Threshold**: Slider to control confidence threshold (0.50 - 0.99)
  - **Lenient (0.50-0.75)**: More matches, higher false positive rate
  - **Balanced (0.80-0.85)**: Recommended for general use
  - **Strict (0.90-0.99)**: Fewer matches, lower false positive rate

**Results Display**:
- Speaker name and confidence percentage
- Visual confidence bar
- Top N matches with scores
- Unknown speaker handling with closest matches

### 2. Enroll Tab

Add new speakers to the system.

**Features**:
- **Speaker Name**: Required field for the person's name
- **Record Audio**: Record voice sample directly
- **Upload File**: Upload audio file
- **Multiple Samples**: Best practice is 3-5 samples per person

**Tips**:
- Use clear, natural speech
- 3-10 seconds of speaking
- Minimize background noise
- Enroll multiple samples for better accuracy

### 3. Manage Tab

View and manage all enrolled speakers.

**Features**:
- **Speaker List**: View all enrolled speakers with avatars
- **Bulk Selection**: Select multiple speakers with checkboxes
- **Delete Individual**: Remove single speaker
- **Delete Selected**: Remove multiple speakers at once
- **Refresh**: Reload speaker list

**Display**:
- Speaker name with colorful avatar (first letter)
- Enrollment status
- Quick delete action

### 4. Settings Tab

View system configuration and perform maintenance.

**System Information**:
- Online/Offline status
- AI Model (Resemblyzer or ECAPA-TDNN)
- Embedding dimensions
- Sample rate (Hz)
- Default threshold
- Version number
- Number of enrolled speakers

**Maintenance**:
- **Rebuild Centroids**: Recompute speaker profiles from raw data
  - Use after enrolling many samples
  - Periodic maintenance (weekly/monthly)
  - If accuracy seems degraded

**Danger Zone**:
- **Reset All Data**: Delete ALL enrolled speakers
  - ⚠️ PERMANENT action - cannot be undone
  - Requires multiple confirmations
  - Use with extreme caution

### 5. API Tab

Quick access to API documentation and examples.

**Features**:
- **Swagger UI**: Interactive API testing interface
- **ReDoc**: Clean, readable documentation
- **Endpoint List**: All available API endpoints with methods
- **Code Examples**: cURL commands for common operations
- **Copy Buttons**: One-click copy of example code

**Endpoints Documented**:
- POST /api/identify - Identify speaker
- POST /api/enroll - Enroll speaker
- GET /api/profiles - List speakers
- POST /api/reset - Delete speaker(s)
- POST /api/rebuild_centroids - Rebuild profiles
- GET /health - Health check
- GET /metrics - Prometheus metrics

---

## Audio Recording

### Browser Requirements

Modern browsers support WebRTC audio recording:
- ✅ Chrome/Edge (recommended)
- ✅ Firefox
- ✅ Safari (iOS 14.3+)
- ❌ Internet Explorer (not supported)

### Permissions

First-time recording requires microphone permission:
1. Click "Start Recording"
2. Browser shows permission prompt
3. Click "Allow"
4. Recording begins

**Troubleshooting**:
- If permission denied, check browser settings
- Chrome: Settings → Privacy → Site Settings → Microphone
- Firefox: Settings → Privacy & Security → Permissions → Microphone

### Recording Tips

**Best Practices**:
- Speak clearly and naturally
- Record 3-10 seconds
- Avoid background noise
- Don't whisper or shout
- Multiple samples improve accuracy

**Audio Quality**:
- Browser automatically captures at appropriate sample rate
- Converted to 16kHz mono server-side
- No need to configure audio settings

---

## File Upload

### Supported Formats

- **WAV** (recommended)
- **MP3**
- **FLAC**
- **M4A**
- **OGG**

### File Requirements

- **Duration**: 2-30 seconds recommended
- **Sample Rate**: Any (auto-converted to 16kHz)
- **Channels**: Mono or stereo (auto-converted)
- **File Size**: < 10 MB

### Upload Methods

**Drag & Drop** (not yet implemented):
- Drag audio file onto upload area
- Drop to select

**Click to Select**:
- Click "Choose Audio File"
- Browse and select file
- Upload begins automatically

---

## Confidence Threshold Guide

The threshold determines how confident the system must be to identify a speaker.

### Threshold Values

| Value | Description | Use Case |
|-------|-------------|----------|
| **0.95-0.99** | Very Strict | Security, authentication, critical systems |
| **0.85-0.94** | Strict | High accuracy requirements, low tolerance for errors |
| **0.80-0.84** | Balanced (Default) | General use, good balance of accuracy |
| **0.75-0.79** | Lenient | Convenience, accepting more matches |
| **0.50-0.74** | Very Lenient | Maximum recall, research, testing |

### Interpreting Scores

**Confidence Scores**:
- **90%+**: Very high confidence - almost certainly correct
- **80-89%**: High confidence - likely correct
- **70-79%**: Moderate confidence - possibly correct
- **60-69%**: Low confidence - questionable
- **<60%**: Very low confidence - probably wrong

### Adjusting Threshold

**Lower threshold (0.70) if**:
- Getting too many "unknown" results
- Speakers are closely related (family members)
- Audio quality varies
- Prioritize catching all matches

**Raise threshold (0.90) if**:
- Getting false positives
- Need high security
- Speakers sound similar
- Prioritize accuracy over coverage

**Real-time Adjustment**:
- Use slider to test different thresholds
- See results immediately
- Find sweet spot for your use case
- Can adjust per-identification

---

## Design & Theme

### Color Scheme

**Dark Blue/Violet Theme**:
- Background: Deep black (#0a0a0f)
- Accents: Blue (#6366f1) and Violet (#8b5cf6)
- Text: Light gray (#e4e4e7) on dark backgrounds
- Borders: Subtle gray tones

### Visual Feedback

**Status Indicators**:
- 🟢 Green: Success, online, good
- 🔵 Blue: Information, primary actions
- 🟡 Yellow: Warning, unknown speaker
- 🔴 Red: Error, danger, offline

**Animations**:
- Smooth transitions (200ms)
- Fade-in for tab changes
- Slide-in for results
- Pulse for recording state
- Glow effects on hover

### Responsive Design

**Breakpoints**:
- Desktop: > 768px (full layout)
- Tablet: 768px (adjusted grids)
- Mobile: < 768px (stacked layout)

**Mobile Optimizations**:
- Touch-friendly buttons
- Readable text sizes
- Simplified navigation
- Vertical stacking

---

## Keyboard Shortcuts

*Not yet implemented - future enhancement*

Planned shortcuts:
- `Ctrl/Cmd + 1-5`: Switch tabs
- `Ctrl/Cmd + R`: Start/stop recording
- `Ctrl/Cmd + U`: Upload file
- `Esc`: Cancel operation

---

## Accessibility

### Features

- ✅ Semantic HTML structure
- ✅ ARIA labels for icons
- ✅ Keyboard navigation
- ✅ High contrast colors
- ✅ Readable font sizes
- ✅ Focus indicators

### Screen Readers

- All buttons have descriptive labels
- Status messages announced
- Form fields properly labeled
- Results clearly structured

---

## Browser Compatibility

### Supported Browsers

| Browser | Version | Support |
|---------|---------|---------|
| Chrome | 90+ | ✅ Full |
| Edge | 90+ | ✅ Full |
| Firefox | 88+ | ✅ Full |
| Safari | 14+ | ✅ Full |
| Opera | 76+ | ✅ Full |
| IE | Any | ❌ None |

### Required Features

- ES6+ JavaScript
- CSS Grid & Flexbox
- WebRTC (for recording)
- Fetch API
- Local Storage
- Media Recorder API

---

## Customization

### Colors

Edit `app/static/css/styles.css` CSS variables:

```css
:root {
    --accent-primary: #6366f1;    /* Primary blue */
    --accent-secondary: #8b5cf6;  /* Secondary violet */
    --bg-primary: #0a0a0f;        /* Main background */
    /* ... more variables ... */
}
```

### Layout

Modify `app/static/index.html`:
- Add/remove tabs
- Reorder sections
- Change grid layouts
- Add custom features

### Functionality

Extend `app/static/js/app.js`:
- Add new API calls
- Custom audio processing
- Additional UI features
- Integration hooks

---

## Troubleshooting

### Interface Not Loading

**Issue**: Blank page or "Web UI not found"

**Solutions**:
1. Check `app/static/` directory exists
2. Verify files present: `index.html`, `css/styles.css`, `js/app.js`
3. Restart FastAPI server
4. Clear browser cache (Ctrl+Shift+R)

### Recording Not Working

**Issue**: "Microphone access denied"

**Solutions**:
1. Grant microphone permission in browser
2. Check system microphone settings
3. Try different browser
4. Use HTTPS (required for some browsers)

### Files Not Uploading

**Issue**: Upload button not responding

**Solutions**:
1. Check file format (WAV/MP3/FLAC)
2. Verify file size < 10 MB
3. Try different file
4. Check browser console for errors

### API Calls Failing

**Issue**: "Network error" or 404

**Solutions**:
1. Verify server running: `curl http://localhost:8080/health`
2. Check API endpoint availability
3. Look at browser Network tab
4. Check server logs

### Styling Issues

**Issue**: Layout broken or colors wrong

**Solutions**:
1. Hard refresh: Ctrl+Shift+R
2. Clear browser cache
3. Check CSS file loaded (Network tab)
4. Try different browser

---

## Performance

### Optimization

**Load Times**:
- First load: ~100-200ms
- Subsequent loads: ~50ms (cached)
- API calls: ~100-500ms (depends on audio processing)

**Best Practices**:
- Cache static files
- Minimize audio file sizes
- Use recommended formats (WAV)
- Batch operations when possible

### Monitoring

Check performance with:
- Browser DevTools → Network tab
- Browser DevTools → Performance tab
- Prometheus metrics at `/metrics`

---

## Future Enhancements

Planned features:
- [ ] Drag-and-drop file upload
- [ ] Bulk enrollment (multiple files)
- [ ] Speaker comparison view
- [ ] Enrollment history/timeline
- [ ] Audio waveform visualization
- [ ] Export/import speaker database
- [ ] Dark/light theme toggle
- [ ] Multi-language support
- [ ] Keyboard shortcuts
- [ ] Mobile app (PWA)

---

For API details, see [API Reference](api.md).
For deployment, see [Deployment Guide](deployment.md).
