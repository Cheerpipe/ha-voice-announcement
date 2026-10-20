# Voice Announcement for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/Cheerpipe/ha-voice-announcement/actions/workflows/validate.yml/badge.svg)](https://github.com/Cheerpipe/ha-voice-announcement/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/Cheerpipe/ha-voice-announcement)](https://github.com/Cheerpipe/ha-voice-announcement/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

*[Leer en español](README.es.md)*

Talk to your house. Press a button on your dashboard and say something, or type a message, and it plays on the speakers you picked: one room, a few of them, or the whole home.

<img src="docs/images/layouts.jpg" alt="The four Voice Announcement layouts" width="620">

## What you get

- **A dashboard card and a badge** that record a voice message from any browser or the Home Assistant app.
- **Typed messages and quick messages.** Add a text-to-speech engine and the same card also reads typed messages aloud. Save the phrases you use most, with an icon if you like, and send them with one tap.
- **Four layouts:** a tile, a large vertical button for popups, a message box like Assist, and voice/text tabs.
- **One speaker or many.** List several speakers and the card shows chips to choose where the message goes, with an *All* shortcut. You can allow several at once or only one at a time, and give each speaker its own name, icon, and color.
- **Hold to talk or tap to talk.** Keyboard friendly, too: hold Space or Enter, and press Enter to send text.
- **Announcement mode.** On speakers that support it, music is lowered during the message and resumes afterwards.
- **Plays on almost anything.** Recordings are converted to MP3 by default, so HomePods, Google and Nest speakers, Sonos, Music Assistant players and most other media players can play them.
- **Restyle everything** with [UIX](https://github.com/Lint-Free-Technology/uix), card-mod, or CSS variables.
- **A visual editor** that looks and works like the built-in Home Assistant card editors, in English and Spanish.
- **Entities for automations and diagnostics.** See what is being received, processed or played and on which speaker, react to new recordings, and spot problems such as a missing ffmpeg.
- **Private by default.** Uploads require a signed-in Home Assistant user who is allowed to control the chosen speakers. Recordings are deleted automatically after 7 days.

## Requirements

- Home Assistant 2026.6 or newer.
- `ffmpeg` and `ffprobe`. They are already included in Home Assistant OS and the official container images.
- A browser or the Home Assistant app with microphone access. Browsers only allow the microphone on **HTTPS** pages (or `http://localhost`), so open Home Assistant through your HTTPS address.
- For typed messages: any text-to-speech integration, such as Home Assistant Cloud, Google Translate, or Piper.

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Cheerpipe&repository=voice-announcement&category=integration)

1. In HACS, open the menu in the top-right corner and choose **Custom repositories**.
2. Add `https://github.com/Cheerpipe/ha-voice-announcement` with the type **Integration**.
3. Find **Voice Announcement**, download it, and restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration** and add **Voice Announcement**.

### Manual

1. Copy `custom_components/voice_announcement` into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant and add the integration from **Settings → Devices & services**.

The card and badge are loaded automatically. You don't need to add a dashboard resource.

## Adding the card

Edit a dashboard, select **Add card**, and search for **Voice Announcement**. Pick one or more speakers and a layout, and you're done. Everything else is optional.

<img src="docs/images/editor.jpg" alt="The Voice Announcement card editor" width="560">

The same settings in YAML:

```yaml
type: custom:voice-announcement-card
entities:
  - media_player.kitchen
```

### Layouts

| Layout | Looks like | Best for |
| --- | --- | --- |
| `horizontal` | A tile card: button beside the text. With text-to-speech, a keyboard button opens the message box. | Compact dashboards. |
| `vertical` | A large button on top, with the message box below. | Popups and phones. |
| `composer` | One message box with the mic beside it, like Assist. The mic turns into a send button as you type. | Talking and typing equally. |
| `tabs` | *Voice* and *Text* tabs. | Keeping voice and text apart. |

`composer` and `tabs` need a text-to-speech engine. Without one, the card shows the `horizontal` layout.

### Choosing between several speakers

Give the card a list of speakers and it shows a chip for each one, in the same order. Tap the chips to decide where the next message goes. The card remembers your choice on each device.

```yaml
type: custom:voice-announcement-card
entities:
  - entity: media_player.kitchen
    name: Kitchen
    icon: mdi:silverware-fork-knife
    color: orange
  - media_player.living_room
  - entity: media_player.bedroom
    icon: mdi:bed
selection_mode: multiple   # or "single" to allow only one speaker at a time
```

Each speaker can be just its entity id or have a `name`, `icon`, and `color` of its own. The color tints the chip when it's selected. In the editor, drag the speakers to change their order and use the pencil to customize one.

With `selection_mode: multiple` you also get an **All** chip. With `single`, picking a speaker replaces the previous one.

### Typed messages and quick messages

Choose a text-to-speech engine in **Text to speech** and the card gets a message box. Quick messages appear as chips you can send with one tap; give them an icon if you like, and drag them in the editor to change their order.

```yaml
type: custom:voice-announcement-card
layout: composer
entity_id:
  - media_player.kitchen
  - media_player.living_room
tts_engine: tts.home_assistant_cloud
tts_language: en-US        # optional
tts_voice: JennyNeural     # optional, only if your engine has voices
tts_cache: true            # optional, reuse audio for repeated messages
quick_messages:
  - message: Dinner is ready
    icon: mdi:silverware-fork-knife
  - message: I'm home
    icon: mdi:home-import-outline
  - We're leaving in 5 minutes
```

Typed messages play on the same speakers as recordings, with the same announcement mode.

### A small intercom for a popup

This section works well on its own or inside a popup. It uses seven speakers named `media_player.player1` to `media_player.player7`:

```yaml
type: grid
cards:
  - type: heading
    heading: Intercom
    icon: mdi:bullhorn
  - type: custom:voice-announcement-card
    layout: vertical
    selection_mode: multiple
    tts_engine: tts.home_assistant_cloud
    quick_messages:
      - message: Dinner is ready
        icon: mdi:silverware-fork-knife
      - Time to go
    entities:
      - media_player.player1
      - media_player.player2
      - media_player.player3
      - media_player.player4
      - media_player.player5
      - media_player.player6
      - media_player.player7
```

If you use [Browser Mod](https://github.com/thomasloven/hass-browser_mod), a button can open the same card in a popup:

```yaml
type: button
name: Intercom
icon: mdi:bullhorn
tap_action:
  action: perform-action
  perform_action: browser_mod.popup
  data:
    browser_id: THIS
    title: Intercom
    content:
      type: custom:voice-announcement-card
      layout: vertical
      tts_engine: tts.home_assistant_cloud
      entities:
        - media_player.player1
        - media_player.player2
        - media_player.player3
        - media_player.player4
        - media_player.player5
        - media_player.player6
        - media_player.player7
```

### Badge

The badge is a compact round button for the top of a view. It records voice and plays on every speaker in its list.

```yaml
type: custom:voice-announcement-badge
entities:
  - media_player.kitchen
```

## Options

| Option | Default | What it does |
| --- | --- | --- |
| `entities` | required | The speakers, in chip order. Each item is an entity id or has `entity`, `name`, `icon`, and `color`. The older `entity_id` (one id or a list) still works. |
| `layout` | `horizontal` | `horizontal`, `vertical`, `composer`, or `tabs`. See [Layouts](#layouts). |
| `recording_mode` | `hold` | `hold` records while you hold the button. `toggle` starts with one tap and sends with the next. |
| `selection_mode` | `multiple` | With several speakers: `multiple` lets you pick any combination, `single` only one at a time. |
| `tts_engine` | – | A text-to-speech entity, such as `tts.home_assistant_cloud`. Turns on typed and quick messages. |
| `tts_language` | engine default | Language for typed messages, such as `es-ES`. Leave it out to use the language set in your text-to-speech integration. |
| `tts_voice` | engine default | Voice name, for engines that offer several. |
| `tts_cache` | `true` | Reuses the generated audio when the same message is sent again, so it plays sooner. |
| `quick_messages` | – | Phrases to send with one tap. Each item is a text or has `message` and `icon`. |
| `active_color` | `red` | A Home Assistant color name (such as `blue` or `primary`) or a hex color. |
| `microphone_icon` | `mdi:microphone` | Icon shown while idle and recording. |
| `speaker_icon` | `mdi:volume-high` | Icon shown while sending and playing. |
| `show_timer` | `true` | Shows the recording time and the selected speakers below the status. |
| `max_duration` | `30` | Recording stops automatically after this many seconds (the server accepts up to 120). |
| `min_duration` | `0.5` | Shorter recordings are discarded, so accidental taps aren't sent. |
| `auto_play` | `true` | Plays the recording as soon as it's uploaded. |
| `announce` | `true` | Uses announcement mode on speakers that support it. |
| `playback_start_delay` | `2` | Seconds the card waits before saying it's playing. Match it to how long your speakers take to start. |

### Audio format options

You rarely need these. The defaults convert every recording to MP3, which almost every speaker can play.

| Option | Default | What it does |
| --- | --- | --- |
| `output_profile` | `default` | The speakers you're sending to: `default` (any speaker), `homepod`, `google_home`, or `custom`. |
| `transcoding` | `always` | `always` converts every recording. `auto` skips conversion when the speaker profile accepts the recorded format, so playback starts a little sooner. `never` never converts and rejects recordings the profile doesn't accept. |
| `input_profile` | `default` | Which recording format the browser tries first: `default`, `chrome`, or `safari`. The editor shows what your current browser will use. |
| `input_mime_candidates` | – | Your own ordered list of recording formats, for example `[audio/mp4, audio/webm;codecs=opus]`. |
| `transcode_target` | – | Conversion settings: `codec` (`mp3` or `aac`), `bitrate` (`32k`–`192k`), `sample_rate` (8000–48000), `channels` (`1` or `2`). |
| `output_passthrough_rules` | – | Formats your speakers play as-is, for example `[{mime_type: audio/mpeg}]`. |

For HomePods, try `input_profile: safari`, `output_profile: homepod`, `transcoding: auto`. For Google and Nest speakers, try `input_profile: chrome`, `output_profile: google_home`, `transcoding: auto`.

## Styling with UIX

Every part of the card can be restyled with [UIX](https://github.com/Lint-Free-Technology/uix). All four layouts share the same elements, so a style works whichever layout you pick. Styles go under `uix: style:`; `:host` is the card itself and `ha-card` its frame. card-mod works the same way under `card_mod: style:`.

```yaml
type: custom:voice-announcement-card
layout: tabs
entities:
  - media_player.kitchen
tts_engine: tts.home_assistant_cloud
uix:
  style: |
    ha-card {
      --voice-announcement-active-color: var(--purple-color);
      border-radius: 24px;
    }
    .quick-message {
      background: color-mix(in srgb, var(--purple-color) 14%, transparent);
      border-color: transparent;
    }
    :host([state="recording"]) ha-card {
      background: color-mix(in srgb, var(--red-color) 8%, var(--card-background-color));
    }
```

### Elements

| Selector | Element |
| --- | --- |
| `ha-card` | The card frame. |
| `.container` | Grid holding everything. Has `.layout-horizontal`, `.layout-vertical`, `.layout-composer`, or `.layout-tabs`. |
| `.tabs`, `.tab`, `.tab[aria-selected="true"]` | The *Voice* and *Text* tabs. |
| `.button-frame`, `.record-button`, `.record-button ha-icon`, `.center-pulse` | The record button, its icon, and the glow while recording. |
| `.text-zone`, `.status`, `.timer` | Status text and the secondary line (timer or speakers). |
| `.compose-toggle` | Keyboard button of the horizontal layout. |
| `.targets`, `.target`, `.target[aria-pressed="true"]`, `.target[data-target="media_player.kitchen"]`, `.target-icon` | Speaker chips, the selected ones, one specific speaker, and its icon. |
| `.quick`, `.quick-message`, `.quick-message ha-icon` | Quick message chips and their icons. |
| `.composer`, `.message`, `.send-button` | Message box, text field, and send button. |

Every element also has a `part` with the same name (for example `part="send"`), and the badge uses `.record-button` too.

### States

The card reflects what it's doing as attributes on `:host`, so you can style each moment:

| Attribute | Values |
| --- | --- |
| `state` | `idle`, `starting`, `recording`, `uploading`, `playing`, `error`, `done` |
| `layout` | `horizontal`, `vertical`, `composer`, `tabs` |
| `tab` | `voice`, `text` (tabs layout) |
| `has-tts`, `has-quick`, `has-targets`, `has-text`, `composing` | Present when text-to-speech is set, there are quick messages, there are several speakers, the message box has text, or the horizontal message box is open. |

For example, `:host([state="playing"]) .status { color: var(--green-color); }`.

### CSS variables

These work from UIX, card-mod, or a theme:

| Variable | Changes |
| --- | --- |
| `--voice-announcement-active-color` | Main color (overrides `active_color`). |
| `--voice-announcement-button-color` / `-button-color-recording` | Button background while idle / while active. |
| `--voice-announcement-button-icon-color` / `-button-icon-color-active` | Icon color while idle / while active. |
| `--voice-announcement-button-size`, `-button-size-horizontal`, `-button-size-composer` | Button size per layout. |
| `--voice-announcement-button-icon-size`, `-button-icon-size-horizontal` | Icon size. |
| `--voice-announcement-button-border`, `-button-border-radius`, `-button-shadow`, `-button-image` | Button shape and decoration. |
| `--voice-announcement-button-recording-animation`, `-pulse-size` | The pulse around the button while recording. |
| `--voice-announcement-center-pulse-color`, `-center-pulse-duration`, `-center-pulse-display-recording` | The glow inside the button (`none` hides it). |
| `--voice-announcement-label-color`, `-label-font-size`, `-label-font-weight` | Status text. |
| `--voice-announcement-timer-color`, `-timer-font-size`, `-timer-display` | Secondary line. |
| `--voice-announcement-card-padding`, `-card-gap`, `-section-gap` | Spacing. |
| `--voice-announcement-targets-justify`, `-chip-border-radius`, `-target-color` | Speaker chips (`-target-color` is set per speaker by its `color`). |
| `--voice-announcement-quick-background`, `-quick-border-radius`, `-quick-justify`, `-quick-icon-color` | Quick message chips. |
| `--voice-announcement-input-background`, `-input-border`, `-input-border-radius` | Message box. |
| `--voice-announcement-send-color`, `-send-icon-color` | Send button. |
| `--voice-announcement-tabs-background`, `-tabs-border-radius`, `-tab-selected-background` | Tabs. |
| `--voice-announcement-badge-size`, `-badge-icon-size`, `-badge-color`, `-badge-color-recording`, `-badge-icon-color`, `-badge-border`, `-badge-border-radius` | The badge. |

Without UIX you can also use `button_css`, `status_css`, `timer_css`, and `text_css` (in the editor under **Custom styles**). They accept plain CSS declarations; only safe visual properties are applied.

## Recordings and services

Recordings are stored in `/config/voice_announcement`. The newest 100 are kept for up to 7 days, and you can browse them under **Media → Voice Announcement**. Typed messages are handled by your text-to-speech integration and aren't stored here. Anyone can use `voice_announcement.play` to replay a recording (`last` plays the newest one) or read a message aloud. It accepts entities, devices, areas, floors and labels as targets:

```yaml
action: voice_announcement.play
target:
  area_id: kitchen
data:
  recording_id: last
```

```yaml
action: voice_announcement.play
target:
  entity_id: media_player.kitchen
data:
  message: Dinner is ready
  tts_engine: tts.home_assistant_cloud
```

Administrators can also use two more actions:

```yaml
action: voice_announcement.cleanup
data:
  keep_days: 1
```

```yaml
action: voice_announcement.delete_recording
data:
  recording_id: 0123456789abcdef0123456789abcdef
```

## Entities

The integration adds a **Voice Announcement** device with these entities. Entity IDs below are the defaults for an English installation.

**Activity**

| Entity | What it shows |
|---|---|
| `sensor.voice_announcement_status` | `idle`, `receiving`, `processing` or `playing`; the most advanced phase wins when several things happen at once. Attributes: `targets`, `type` (`voice` or `tts`), `user`, `recording_id`, `started_at` and `active_jobs` with every upload and announcement in progress. |
| `binary_sensor.voice_announcement_receiving` | On while an upload is arriving. `targets` says where it is going. |
| `binary_sensor.voice_announcement_processing` | On while an upload is validated and converted. |
| `binary_sensor.voice_announcement_playing` | On while an announcement plays anywhere. |
| `binary_sensor.voice_announcement_playing_on_<speaker>` | One per speaker that has received an announcement; on while it plays there. |

**Recordings and announcements**

| Entity | What it shows |
|---|---|
| `sensor.voice_announcement_last_recording` | When the last recording was made, with its `recording_id`, `media_source_id`, `url`, `targets`, `user` and `duration`. |
| `sensor.voice_announcement_last_recording_duration` | Its length in seconds. |
| `sensor.voice_announcement_recordings_today` | Recordings since midnight. |
| `sensor.voice_announcement_last_announcement` | When the last announcement started, with its type, speakers, result (`ok`, `partial` or `failed`) and why it ended. |
| `event.voice_announcement_recording` | Fires `recorded`, `deleted`, `cleanup` and `failed` (upload failed). |
| `event.voice_announcement_announcement` | Fires `started`, `finished` and `failed`. |
| `button.voice_announcement_clean_up_old_recordings` | Deletes recordings older than 7 days. |
| `button.voice_announcement_delete_last_recording` | Deletes the newest recording. |

**Diagnostics**: stored recordings, storage used, oldest recording, last upload status (with the reason when it failed), failed uploads, last processing time (with each step's timing), transcoded uploads (%), active uploads, last cleanup, failed playbacks, and two problem sensors that turn on when **FFmpeg** or **FFprobe** is missing.

### When a message counts as playing

Announcements sent by the card, or by the `voice_announcement.play` action, are tracked from the moment the speakers are asked to play until the message's length has passed. Speakers that report what they play end it earlier when they stop, or later if they are still playing it (up to one extra minute). Announcements sent straight to `media_player.play_media` or `tts.speak` aren't tracked.

### Events for automations

Besides the event entities, each step fires an event you can use as a trigger: `voice_announcement_receiving_started`, `voice_announcement_processing_started`, `voice_announcement_recorded`, `voice_announcement_upload_failed`, `voice_announcement_deleted`, `voice_announcement_cleanup`, `voice_announcement_playback_started`, `voice_announcement_playback_finished` and `voice_announcement_playback_failed`. They carry the `recording_id`, `targets`, `type` and `user` when they apply.

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.voice_announcement_playing_on_living_room
    to: "on"
actions:
  - action: media_player.volume_mute
    target:
      entity_id: media_player.living_room_tv
    data:
      is_volume_muted: true
```

## Troubleshooting

**The card isn't in the card picker.** Restart Home Assistant after installing, make sure the integration is added under **Devices & services**, then reload the browser. In the Home Assistant app, pull down to refresh or close and reopen it.

**"Microphone access needs HTTPS".** Browsers only allow the microphone on secure pages. Open Home Assistant through its HTTPS address (for example your Home Assistant Cloud or reverse-proxy URL).

**"Microphone access was denied".** Allow the microphone for your Home Assistant address in the browser's site settings, or for the Home Assistant app in your phone's settings.

**The message uploads but nothing plays.** Check that the speaker can play media from Home Assistant: try it from **Media** in the sidebar. If the card shows an error after "Sending…", the speaker refused the message. Hover over the error to see the technical reason, or check the Home Assistant log.

**Typed messages show "Couldn't play on the speakers" with "Invalid options" in the tooltip.** Your engine doesn't accept the `tts_voice` or `tts_language` you set. Clear them to use the engine's defaults.

**Playback starts late.** Set `transcoding: auto` with the speaker profile that matches your speakers, and adjust `playback_start_delay`. The log line *Processed Voice Announcement upload* shows how long each step took.

**Errors mentioning ffmpeg or ffprobe.** Install them where Home Assistant runs. Home Assistant OS and the official containers already include them.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pytest
.venv/bin/ruff check .
node --check custom_components/voice_announcement/www/voice-announcement-card.js
```

The tests run real uploads, so `ffmpeg` and `ffprobe` must be installed.

## License

[MIT](LICENSE)
