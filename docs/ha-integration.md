# Home Assistant Integration Guide

Complete guide to integrating Speaker-ID with Home Assistant for voice-based automations.

---

## Prerequisites

- Home Assistant installed and running
- Speaker-ID service running on your network
- Access to `configuration.yaml`
- Basic understanding of Home Assistant automations

---

## Home Assistant Assist Pipeline Integration

**This is the recommended integration method** for using Speaker-ID with Home Assistant's built-in voice assistant.

The Home Assistant Assist Pipeline allows you to create personalized voice-controlled automations where the system knows who is speaking. This enables truly personalized smart home experiences.

### What is the Assist Pipeline?

Home Assistant's Assist Pipeline is the complete voice assistant stack that includes:
- **Wake word detection** (e.g., "Hey Jarvis")
- **Speech-to-text** (converting voice to text)
- **Intent recognition** (understanding commands)
- **Text-to-speech** (responding with voice)

Speaker-ID integrates into this pipeline to add **speaker identification**, allowing your assistant to know *who* is speaking and personalize responses accordingly.

### Architecture Overview

```
User speaks → Wake Word → Audio Recording → Speaker-ID API → Intent Processing → Personalized Action
```

### Complete Assist Pipeline Setup

#### Step 1: Install Required Add-ons

Install these Home Assistant add-ons:

1. **Whisper** (Speech-to-Text)
   - Go to Settings → Add-ons → Add-on Store
   - Search for "Whisper" and install
   - Start the add-on

2. **Piper** (Text-to-Speech)
   - Install from Add-on Store
   - Start the add-on

3. **Wyoming Satellite** (Optional - for dedicated voice terminals)
   - For ESPHome devices or separate microphone stations

#### Step 2: Configure Assist Pipeline

**configuration.yaml**:
```yaml
# Enable Assist
assist_pipeline:

# Configure Wyoming protocol for Whisper (STT)
wyoming:
  - name: "Whisper STT"
    uri: "tcp://localhost:10300"
    platform: stt

# Configure Wyoming protocol for Piper (TTS)
  - name: "Piper TTS"
    uri: "tcp://localhost:10200"
    platform: tts

# Speaker-ID REST commands
rest_command:
  identify_speaker_from_assist:
    url: "http://192.168.1.100:8080/api/identify"
    method: POST
    content_type: "multipart/form-data"
    payload: "file={{ audio_file }}&threshold=0.82"

# Store identified speaker
input_text:
  current_speaker:
    name: "Current Speaker"
    initial: "unknown"

  last_command_speaker:
    name: "Last Command Speaker"
    initial: "unknown"

# Template sensor for speaker display
template:
  - sensor:
      - name: "Active Speaker"
        state: "{{ states('input_text.current_speaker') }}"
        icon: mdi:account-voice
```

#### Step 3: Create Assist Pipeline with Speaker Identification

**automations.yaml**:
```yaml
# Automation 1: Capture audio when Assist is triggered
- alias: "Assist - Identify Speaker"
  description: "Identify who is speaking when Assist wake word is detected"
  trigger:
    - platform: event
      event_type: assist_pipeline_start
  action:
    # Get the audio file path from the pipeline event
    - variables:
        audio_path: "{{ trigger.event.data.audio_path | default('/tmp/assist_audio.wav') }}"

    # Call Speaker-ID API
    - service: rest_command.identify_speaker_from_assist
      data:
        audio_file: "{{ audio_path }}"

    # Store the result (this will be populated by response)
    - delay:
        milliseconds: 500

    # Update current speaker
    - service: input_text.set_value
      target:
        entity_id: input_text.current_speaker
      data:
        value: "{{ state_attr('rest_command.identify_speaker_from_assist', 'speaker') | default('unknown') }}"

# Automation 2: Store speaker when command is executed
- alias: "Assist - Store Command Speaker"
  description: "Remember who gave the last voice command"
  trigger:
    - platform: event
      event_type: assist_pipeline_end
  condition:
    - condition: template
      value_template: "{{ states('input_text.current_speaker') != 'unknown' }}"
  action:
    - service: input_text.set_value
      target:
        entity_id: input_text.last_command_speaker
      data:
        value: "{{ states('input_text.current_speaker') }}"
```

#### Step 4: Create Personalized Sentence Triggers

Home Assistant allows you to define custom voice commands. Combine these with speaker identification for personalized responses.

**configuration.yaml**:
```yaml
conversation:
  intents:
    TurnOnLights:
      - "turn on [the] lights"
      - "lights on"

    GoodMorning:
      - "good morning"
      - "morning"

    WhatIsTheWeather:
      - "what's the weather"
      - "weather forecast"

    PlayMusic:
      - "play [my] music"
      - "play some music"
```

**automations.yaml**:
```yaml
# Personalized Good Morning
- alias: "Assist - Good Morning (Personalized)"
  trigger:
    - platform: conversation
      command: "good morning"
  action:
    - choose:
        # Alice's good morning
        - conditions:
            - condition: state
              entity_id: input_text.current_speaker
              state: "Alice"
          sequence:
            - service: tts.speak
              data:
                entity_id: media_player.living_room_speaker
                message: >
                  Good morning Alice! It's {{ now().strftime('%I:%M %p') }}.
                  The temperature is {{ states('sensor.outdoor_temperature') }}°C.
                  Your calendar shows {{ state_attr('calendar.alice', 'message') }}.
            - service: light.turn_on
              target:
                entity_id: light.bedroom_alice
              data:
                brightness_pct: 50
            - service: climate.set_temperature
              target:
                entity_id: climate.bedroom
              data:
                temperature: 21

        # Bob's good morning
        - conditions:
            - condition: state
              entity_id: input_text.current_speaker
              state: "Bob"
          sequence:
            - service: tts.speak
              data:
                entity_id: media_player.living_room_speaker
                message: >
                  Good morning Bob! The news headlines are ready.
                  Your commute shows {{ states('sensor.waze_travel_time') }} minutes to work.
            - service: light.turn_on
              target:
                entity_id: light.office
            - service: media_player.play_media
              target:
                entity_id: media_player.kitchen_speaker
              data:
                media_content_type: "playlist"
                media_content_id: "spotify:playlist:morning_news"

      # Default for unknown speaker
      default:
        - service: tts.speak
          data:
            entity_id: media_player.living_room_speaker
            message: "Good morning! I don't recognize your voice yet. Would you like to enroll?"

# Personalized Music
- alias: "Assist - Play Music (Personalized)"
  trigger:
    - platform: conversation
      command: "play music"
  action:
    - choose:
        - conditions:
            - condition: state
              entity_id: input_text.current_speaker
              state: "Alice"
          sequence:
            - service: media_player.play_media
              target:
                entity_id: media_player.spotify
              data:
                media_content_type: playlist
                media_content_id: "spotify:playlist:alice_favorites"

        - conditions:
            - condition: state
              entity_id: input_text.current_speaker
              state: "Bob"
          sequence:
            - service: media_player.play_media
              target:
                entity_id: media_player.spotify
              data:
                media_content_type: playlist
                media_content_id: "spotify:playlist:bob_rock"

      default:
        - service: media_player.play_media
          target:
            entity_id: media_player.spotify
          data:
            media_content_type: playlist
            media_content_id: "spotify:playlist:house_default"

# Personalized Lighting Control
- alias: "Assist - Turn On Lights (Personalized)"
  trigger:
    - platform: conversation
      command: "turn on lights"
  action:
    - choose:
        # Alice prefers warm, dimmer lights
        - conditions:
            - condition: state
              entity_id: input_text.current_speaker
              state: "Alice"
          sequence:
            - service: light.turn_on
              target:
                entity_id: light.living_room
              data:
                brightness_pct: 60
                color_temp: 370

        # Bob prefers bright, cool lights
        - conditions:
            - condition: state
              entity_id: input_text.current_speaker
              state: "Bob"
          sequence:
            - service: light.turn_on
              target:
                entity_id: light.living_room
              data:
                brightness_pct: 100
                color_temp: 250

      # Default lighting
      default:
        - service: light.turn_on
          target:
            entity_id: light.living_room
          data:
            brightness_pct: 80
```

#### Step 5: Voice Enrollment via Assist

Create a conversational enrollment flow:

**automations.yaml**:
```yaml
- alias: "Assist - Voice Enrollment Trigger"
  trigger:
    - platform: conversation
      command: "enroll my voice"
  action:
    - service: tts.speak
      data:
        entity_id: media_player.living_room_speaker
        message: "Sure! What's your name?"

    - service: input_text.set_value
      target:
        entity_id: input_text.enrollment_state
      data:
        value: "awaiting_name"

- alias: "Assist - Voice Enrollment Name Received"
  trigger:
    - platform: event
      event_type: assist_pipeline_end
  condition:
    - condition: state
      entity_id: input_text.enrollment_state
      state: "awaiting_name"
  action:
    # Extract name from voice command
    - variables:
        speaker_name: "{{ trigger.event.data.transcript }}"

    - service: input_text.set_value
      target:
        entity_id: input_text.enrollment_name
      data:
        value: "{{ speaker_name }}"

    - service: tts.speak
      data:
        entity_id: media_player.living_room_speaker
        message: "Got it, {{ speaker_name }}. Please say a sentence so I can learn your voice."

    - service: input_text.set_value
      target:
        entity_id: input_text.enrollment_state
      data:
        value: "recording_sample"

- alias: "Assist - Voice Enrollment Sample Recorded"
  trigger:
    - platform: event
      event_type: assist_pipeline_end
  condition:
    - condition: state
      entity_id: input_text.enrollment_state
      state: "recording_sample"
  action:
    # Get audio file and enroll
    - variables:
        audio_path: "{{ trigger.event.data.audio_path }}"
        speaker_name: "{{ states('input_text.enrollment_name') }}"

    - service: rest_command.enroll_speaker
      data:
        name: "{{ speaker_name }}"
        file_path: "{{ audio_path }}"

    - service: tts.speak
      data:
        entity_id: media_player.living_room_speaker
        message: "Perfect! I've enrolled {{ speaker_name }}. Try saying 'Good morning' and I'll recognize you."

    - service: input_text.set_value
      target:
        entity_id: input_text.enrollment_state
      data:
        value: "idle"
```

#### Step 6: Dashboard Card for Pipeline Status

**ui-lovelace.yaml**:
```yaml
type: vertical-stack
title: "Voice Assistant Status"
cards:
  - type: entities
    entities:
      - entity: sensor.active_speaker
        name: "Current Speaker"
        icon: mdi:account-voice
      - entity: input_text.last_command_speaker
        name: "Last Command By"
      - entity: sensor.speaker_id_health
        name: "Speaker-ID Service"

  - type: button
    name: "Enroll My Voice"
    tap_action:
      action: call-service
      service: conversation.process
      service_data:
        text: "enroll my voice"

  - type: history-graph
    title: "Speaker Activity"
    entities:
      - sensor.active_speaker
    hours_to_show: 24
```

### Advanced Assist Pipeline Features

#### Multi-Room Speaker Identification

Track which room each person is in based on where they spoke:

```yaml
automation:
  - alias: "Track Speaker Location by Room"
    trigger:
      - platform: state
        entity_id: input_text.current_speaker
    action:
      - service: input_text.set_value
        target:
          entity_id: "input_text.{{ states('input_text.current_speaker') }}_location"
        data:
          value: "{{ trigger.event.data.device_id | device_attr('name') }}"
```

#### Speaker-Based Access Control

Only allow certain speakers to control specific devices:

```yaml
automation:
  - alias: "Assist - Unlock Front Door (Authorized Only)"
    trigger:
      - platform: conversation
        command: "unlock front door"
    condition:
      - condition: or
        conditions:
          - condition: state
            entity_id: input_text.current_speaker
            state: "Alice"
          - condition: state
            entity_id: input_text.current_speaker
            state: "Bob"
    action:
      - service: lock.unlock
        target:
          entity_id: lock.front_door
      - service: tts.speak
        data:
          entity_id: media_player.entrance_speaker
          message: "Front door unlocked for {{ states('input_text.current_speaker') }}"

    # Deny access for unknown speakers
    alternative:
      - service: tts.speak
        data:
          entity_id: media_player.entrance_speaker
          message: "Sorry, I don't recognize your voice. Access denied."
      - service: notify.mobile_app
        data:
          message: "Unknown person attempted to unlock front door"
          title: "Security Alert"
```

#### Context-Aware Responses Based on History

```yaml
automation:
  - alias: "Assist - Smart Responses Based on Speaker"
    trigger:
      - platform: conversation
        command: "I'm home"
    action:
      - choose:
          - conditions:
              - condition: state
                entity_id: input_text.current_speaker
                state: "Alice"
              - condition: state
                entity_id: calendar.alice
                state: "on"
            sequence:
              - service: tts.speak
                data:
                  message: >
                    Welcome home Alice! You have {{ state_attr('calendar.alice', 'message') }}
                    in {{ relative_time(state_attr('calendar.alice', 'start_time')) }}.
                    Would you like me to start dinner prep mode?
```

### Troubleshooting Assist Pipeline Integration

**Issue: Speaker-ID not recognizing voices in pipeline**
- Ensure audio format from Assist is compatible (16kHz WAV recommended)
- Check that audio file path is accessible to Speaker-ID service
- Verify network connectivity between Home Assistant and Speaker-ID

**Issue: Delay in speaker identification**
- Consider lowering audio quality in Whisper settings
- Use Resemblyzer instead of ECAPA for faster inference
- Add caching to avoid re-identifying same speaker repeatedly

**Issue: Wake word triggers but no identification**
- Check that `assist_pipeline_start` event is firing: Developer Tools → Events → Listen for `assist_pipeline_start`
- Verify automation is triggering: Developer Tools → Automations
- Enable debug logging for Assist pipeline

**Issue: Audio file not saved for identification**
- Some Assist configurations don't save audio to disk by default
- You may need to use Wyoming Satellite with file recording enabled
- Alternative: Use ESPHome device with voice_assistant component

### Performance Considerations

- **Latency**: Speaker identification adds ~100-200ms to pipeline (imperceptible to users)
- **Accuracy**: Enroll 3-5 samples per person for best results with Assist pipeline
- **Caching**: Store last speaker ID for 30 seconds to avoid repeated API calls for multi-turn conversations

### Privacy & Security

- Audio is processed locally (no cloud required)
- Voice embeddings cannot be reversed to reconstruct audio
- Speaker-ID only stores mathematical representations of voices
- All processing happens on your local network

---

## Alternative Integration Methods

If you're not using the Assist Pipeline, here are other ways to integrate Speaker-ID:

### Method 1: REST Command (Recommended for Beginners)

The simplest way to call Speaker-ID from Home Assistant.

**Add to `configuration.yaml`**:

```yaml
rest_command:
  enroll_speaker:
    url: "http://192.168.1.100:8080/api/enroll"
    method: POST
    content_type: "multipart/form-data"
    payload: "name={{ name }}&file={{ file_path }}"

  identify_speaker:
    url: "http://192.168.1.100:8080/api/identify"
    method: POST
    content_type: "multipart/form-data"
    payload: "threshold={{ threshold | default(0.82) }}&file={{ file_path }}"
```

Replace `192.168.1.100` with your Speaker-ID server IP.

**Usage in Automation**:

```yaml
automation:
  - alias: "Identify Speaker from Recording"
    trigger:
      - platform: event
        event_type: audio_recorded
    action:
      - service: rest_command.identify_speaker
        data:
          file_path: "{{ trigger.event.data.file_path }}"
          threshold: 0.82
```

### Method 2: RESTful Sensor (For Reading Profiles)

Monitor enrolled speakers as a sensor.

```yaml
sensor:
  - platform: rest
    name: "Enrolled Speakers"
    resource: "http://192.168.1.100:8080/api/profiles"
    method: GET
    value_template: "{{ value_json.profiles | length }}"
    json_attributes:
      - profiles
    scan_interval: 300  # Update every 5 minutes
```

### Method 3: Node-RED (Advanced)

For complex workflows with visual programming.

**Node-RED Flow**:
1. Add HTTP Request node
2. Configure:
   - Method: POST
   - URL: `http://192.168.1.100:8080/api/identify`
   - Upload file in body
3. Connect to function node to process response
4. Trigger Home Assistant services based on result

---

## Complete Integration Example

### Scenario: Personalized Good Morning Routine

**Goal**: When someone says "Good morning", identify them and provide a personalized response.

**Step 1: Configuration**

```yaml
# configuration.yaml

# REST command for identification
rest_command:
  identify_voice:
    url: "http://192.168.1.100:8080/api/identify"
    method: POST
    payload: "file={{ file_path }}&threshold=0.82"

# Input to store last identified speaker
input_text:
  last_speaker:
    name: Last Identified Speaker
    initial: unknown

# Input to store audio file path
input_text:
  last_audio_file:
    name: Last Audio File Path
```

**Step 2: Automation**

```yaml
# automations.yaml

- alias: "Voice Identification Trigger"
  description: "Triggered when wake word detected"
  trigger:
    - platform: state
      entity_id: binary_sensor.wake_word_detected
      to: "on"
  action:
    # Step 1: Record audio (using your mic integration)
    - service: media_player.play_media
      target:
        entity_id: media_player.microphone
      data:
        media_content_type: "recording"
        duration: 5

    # Step 2: Save file path
    - service: input_text.set_value
      target:
        entity_id: input_text.last_audio_file
      data:
        value: "/config/www/recordings/last.wav"

    # Step 3: Identify speaker
    - service: rest_command.identify_voice
      data:
        file_path: "/config/www/recordings/last.wav"

    # Step 4: Parse response and store speaker
    - service: input_text.set_value
      target:
        entity_id: input_text.last_speaker
      data:
        value: "{{ state_attr('rest_command.identify_voice', 'speaker') }}"

- alias: "Personalized Good Morning - Alice"
  trigger:
    - platform: state
      entity_id: input_text.last_speaker
      to: "Alice"
  condition:
    - condition: time
      after: "06:00:00"
      before: "10:00:00"
  action:
    - service: tts.google_translate_say
      data:
        message: "Good morning Alice! It's {{ now().strftime('%H:%M') }}. Would you like me to turn on the coffee maker?"
    - service: light.turn_on
      target:
        entity_id: light.bedroom_alice
      data:
        brightness: 50

- alias: "Personalized Good Morning - Bob"
  trigger:
    - platform: state
      entity_id: input_text.last_speaker
      to: "Bob"
  condition:
    - condition: time
      after: "06:00:00"
      before: "10:00:00"
  action:
    - service: tts.google_translate_say
      data:
        message: "Good morning Bob! The news is ready and your office lights are on."
    - service: light.turn_on
      target:
        entity_id: light.office
```

---

## Working with Audio

### Recording Audio in Home Assistant

**Option 1: ESPHome Microphone**

```yaml
# esphome_device.yaml
microphone:
  - platform: i2s_audio
    id: mic
    adc_type: external
    i2s_din_pin: GPIO32

voice_assistant:
  microphone: mic
  on_start:
    - lambda: |-
        // Start recording
  on_end:
    - lambda: |-
        // Save to file
```

**Option 2: Wyoming Protocol**

Use Wyoming satellite for voice recording, then pass audio to Speaker-ID.

**Option 3: Manual Upload via Dashboard**

Create a file upload card in Lovelace dashboard for manual enrollment.

### Audio File Storage

Store audio files in `/config/www/recordings/` for easy access:

```bash
# Create directory in Home Assistant
mkdir -p /config/www/recordings
chmod 755 /config/www/recordings
```

Files will be accessible at `http://homeassistant.local:8123/local/recordings/`

---

## Enrollment Workflow

### Automatic Enrollment Script

```yaml
# scripts.yaml
enroll_speaker_script:
  alias: "Enroll Speaker"
  fields:
    name:
      description: "Name of the speaker"
      example: "Alice"
    file_path:
      description: "Path to audio file"
      example: "/config/www/recordings/alice1.wav"
  sequence:
    - service: rest_command.enroll_speaker
      data:
        name: "{{ name }}"
        file_path: "{{ file_path }}"
    - service: notify.mobile_app
      data:
        message: "Enrolled voice sample for {{ name }}"
```

### Enrollment via Dashboard

Create a Lovelace card for enrollment:

```yaml
# ui-lovelace.yaml
type: vertical-stack
cards:
  - type: entities
    title: "Speaker Enrollment"
    entities:
      - input_text.speaker_name
      - input_text.audio_file_path
  - type: button
    name: "Enroll Speaker"
    tap_action:
      action: call-service
      service: script.enroll_speaker_script
      service_data:
        name: "{{ states('input_text.speaker_name') }}"
        file_path: "{{ states('input_text.audio_file_path') }}"
```

---

## Advanced Automation Ideas

### 1. Room Presence Detection

```yaml
automation:
  - alias: "Track Speaker Location"
    trigger:
      - platform: state
        entity_id: input_text.last_speaker
    action:
      - service: input_text.set_value
        target:
          entity_id: "input_text.{{ states('input_text.last_speaker') }}_location"
        data:
          value: "{{ trigger.from_state.attributes.room }}"
```

### 2. Multi-Factor Authentication

```yaml
automation:
  - alias: "Voice + PIN Unlock"
    trigger:
      - platform: state
        entity_id: input_text.last_speaker
    condition:
      - condition: and
        conditions:
          - condition: template
            value_template: "{{ states('input_text.last_speaker') == 'Alice' }}"
          - condition: state
            entity_id: input_text.pin_code
            state: "1234"
    action:
      - service: lock.unlock
        target:
          entity_id: lock.front_door
```

### 3. Context-Aware Responses

```yaml
automation:
  - alias: "Context-Aware Assistant"
    trigger:
      - platform: state
        entity_id: input_text.last_speaker
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ states('input_text.last_speaker') == 'Alice' }}"
              - condition: state
                entity_id: media_player.living_room_tv
                state: "playing"
            sequence:
              - service: media_player.media_pause
                target:
                  entity_id: media_player.living_room_tv
              - service: tts.speak
                data:
                  message: "Pausing your show, Alice."
```

---

## Monitoring & Debugging

### Check Speaker-ID Status

```yaml
sensor:
  - platform: rest
    name: "Speaker ID Health"
    resource: "http://192.168.1.100:8080/health"
    value_template: "{{ value_json.status }}"
    scan_interval: 60
```

### Log Identification Events

```yaml
automation:
  - alias: "Log Speaker Identifications"
    trigger:
      - platform: state
        entity_id: input_text.last_speaker
    action:
      - service: logbook.log
        data:
          name: "Speaker Identified"
          message: "Identified {{ states('input_text.last_speaker') }} with confidence {{ state_attr('input_text.last_speaker', 'confidence') }}"
```

### Notification on Unknown Speaker

```yaml
automation:
  - alias: "Alert on Unknown Speaker"
    trigger:
      - platform: state
        entity_id: input_text.last_speaker
        to: "unknown"
    action:
      - service: notify.mobile_app
        data:
          message: "Unknown speaker detected!"
          title: "Security Alert"
```

---

## Troubleshooting

### Common Issues

**1. "Connection refused" error**
- Check Speaker-ID is running: `docker ps`
- Verify IP address in configuration
- Check firewall rules

**2. Audio file not found**
- Ensure file path is absolute
- Check file permissions (must be readable)
- Verify file exists: `ls -la /path/to/file.wav`

**3. Always returns "unknown"**
- Lower threshold: try 0.75 instead of 0.82
- Check audio quality and format
- Verify speakers are enrolled: `curl http://IP:8080/api/profiles`

**4. Slow response**
- Check server CPU usage
- Consider using Resemblyzer instead of ECAPA
- Reduce audio file size/duration

### Debug Mode

Enable debug logging in Home Assistant:

```yaml
logger:
  default: info
  logs:
    homeassistant.components.rest_command: debug
    homeassistant.components.rest: debug
```

---

## Security Considerations

### Network Security

1. **Use local network only**: Don't expose Speaker-ID to internet
2. **Firewall rules**: Block port 8080 from WAN
3. **VPN access**: Use VPN for remote access

### Authentication

Add authentication to Speaker-ID via reverse proxy (nginx):

```nginx
location /api {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8080;
}
```

### Privacy

- Voice embeddings cannot be reversed to audio
- No cloud connection required
- All data stays local
- Regular database backups recommended

---

## Performance Tips

1. **Enroll multiple samples**: 3-5 per person for best accuracy
2. **Use Resemblyzer**: Faster for real-time use
3. **Cache results**: Store last identification to avoid repeated calls
4. **Batch operations**: Enroll multiple samples at once
5. **Monitor metrics**: Use Prometheus endpoint for performance tracking

---

## Example: Complete Smart Home Setup

This example shows a full integration with multiple family members.

**Configuration**:
```yaml
# Track all family members
input_text:
  last_speaker:
    name: Last Speaker
  alice_location:
    name: Alice Location
  bob_location:
    name: Bob Location

# REST commands
rest_command:
  identify_voice:
    url: "http://192.168.1.100:8080/api/identify"
    method: POST
```

**Automations**:
```yaml
# Welcome home greeting
- alias: "Welcome Home - Personalized"
  trigger:
    - platform: state
      entity_id: input_text.last_speaker
  action:
    - service: tts.speak
      data:
        message: >
          Welcome home {{ states('input_text.last_speaker') }}!
          The temperature is {{ states('sensor.living_room_temperature') }}°C.
    - service: light.turn_on
      target:
        entity_id: "light.{{ states('input_text.last_speaker') }}_room"

# Music preferences
- alias: "Music by Speaker"
  trigger:
    - platform: state
      entity_id: input_text.last_speaker
      to: "Alice"
  action:
    - service: media_player.play_media
      target:
        entity_id: media_player.spotify
      data:
        media_content_type: playlist
        media_content_id: "spotify:playlist:alice_favorites"
```

---

For API details, see [API Reference](api.md).
