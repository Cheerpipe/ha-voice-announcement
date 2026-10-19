const VOICE_ANNOUNCEMENT_TAG = "voice-announcement-card";
const VOICE_ANNOUNCEMENT_BADGE_TAG = "voice-announcement-badge";
const EDITOR_TAG = "voice-announcement-card-editor";
const DOCUMENTATION_URL = "https://github.com/Cheerpipe/voice-announcement";

const DEFAULT_CONFIG = {
  layout: "horizontal",
  recording_mode: "hold",
  selection_mode: "multiple",
  max_duration: 30,
  min_duration: 0.5,
  auto_play: true,
  announce: true,
  show_timer: true,
  playback_start_delay: 2,
  microphone_icon: "mdi:microphone",
  speaker_icon: "mdi:volume-high",
  active_color: "red",
  input_profile: "default",
  output_profile: "default",
  transcoding: "always",
  button_css: "",
  status_css: "",
  timer_css: "",
  text_css: "",
};

const INPUT_PROFILES = {
  default: ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"],
  chrome: ["audio/mp4", "audio/webm;codecs=opus", "audio/ogg;codecs=opus"],
  safari: ["audio/mp4", "audio/webm;codecs=opus", "audio/ogg;codecs=opus"],
};
const INPUT_MIME_OPTIONS = [
  "audio/webm;codecs=opus",
  "audio/mp4",
  "audio/ogg;codecs=opus",
  "audio/wav",
  "audio/mpeg",
];
const OUTPUT_PROFILES = ["default", "homepod", "google_home", "custom"];
const TRANSCODING_MODES = ["always", "auto", "never"];
const RECORDING_MODES = ["hold", "toggle"];
const SELECTION_MODES = ["multiple", "single"];
const CARD_LAYOUTS = ["horizontal", "vertical"];
const TRANSCODE_FIELDS = {
  transcode_codec: { key: "codec", options: ["mp3", "aac"] },
  transcode_bitrate: { key: "bitrate", options: ["32k", "48k", "64k", "96k", "128k", "160k", "192k"] },
  transcode_sample_rate: { key: "sample_rate", options: ["16000", "22050", "24000", "32000", "44100", "48000"] },
  transcode_channels: { key: "channels", options: ["1", "2"] },
};
const MEDIA_ANNOUNCE_FEATURE = 1048576;
const MAX_TARGETS = 20;

const AUDIO_BITS_PER_SECOND = 48000;
const RECORDING_TIMESLICE_MS = 250;
const RECORDING_STOP_TIMEOUT_MS = 5000;
const FALLBACK_SAMPLE_RATE = 16000;
const FALLBACK_BUFFER_SIZE = 4096;
const PLAYBACK_STATUS_MIN_MS = 1000;
const PLAYBACK_STATUS_PADDING_MS = 500;
const ERROR_STATUS_MS = 5000;
const UPLOAD_TIMEOUT_MS = 60000;
const RESPONSE_BODY_TIMEOUT_MS = 10000;
const MAX_ERROR_LENGTH = 120;

const MAX_CUSTOM_CSS_LENGTH = 2000;
const BLOCKED_INLINE_CSS_PATTERN =
  /(?:@import|url\s*\(|image-set\s*\(|expression\s*\(|javascript\s*:|data\s*:|vbscript\s*:|behavior\s*:|-moz-binding|<\/style|<|>)/i;
const SAFE_BUTTON_CSS_PROPERTIES = new Set([
  "animation",
  "animation-delay",
  "animation-direction",
  "animation-duration",
  "animation-fill-mode",
  "animation-iteration-count",
  "animation-name",
  "animation-timing-function",
  "background",
  "background-color",
  "border",
  "border-color",
  "border-radius",
  "border-style",
  "border-width",
  "box-shadow",
  "color",
  "filter",
  "opacity",
  "outline",
  "outline-color",
  "outline-offset",
  "outline-style",
  "outline-width",
  "text-shadow",
  "transform",
]);
const SAFE_STATUS_CSS_PROPERTIES = new Set([
  "color",
  "display",
  "font",
  "font-family",
  "font-feature-settings",
  "font-size",
  "font-style",
  "font-variant",
  "font-variant-numeric",
  "font-weight",
  "letter-spacing",
  "line-height",
  "margin",
  "opacity",
  "padding",
  "text-align",
  "text-shadow",
  "text-transform",
  "visibility",
  "white-space",
]);
const SAFE_TEXT_CSS_PROPERTIES = new Set([
  ...SAFE_STATUS_CSS_PROPERTIES,
  "align-content",
  "align-items",
  "gap",
  "justify-content",
  "justify-items",
]);

const STRINGS = {
  en: {
    "card.hold": "Hold to talk",
    "card.toggle": "Tap to talk",
    "card.choose_target": "Choose a speaker",
    "card.starting": "Getting ready…",
    "card.release": "Release to send",
    "card.tap_send": "Tap to send",
    "card.finishing": "Finishing…",
    "card.sending": "Sending…",
    "card.starting_playback": "Starting playback…",
    "card.playing": "Playing on {target}",
    "card.sent": "Sent",
    "card.speakers": "{count} speakers",
    "card.all": "All",
    "card.aria": "Record a voice announcement",
    "card.targets_aria": "Speakers",
    "error.unsupported": "This browser can't record audio",
    "error.insecure": "Microphone access needs HTTPS",
    "error.mic_denied": "Microphone access was denied",
    "error.no_mic": "No microphone found",
    "error.start": "Couldn't start recording",
    "error.stop": "Couldn't stop recording",
    "error.too_short": "Recording too short",
    "error.empty": "The recording is empty",
    "error.send": "Couldn't send the announcement",
    "error.no_api": "Home Assistant isn't connected",
    "editor.appearance": "Appearance",
    "editor.recording": "Recording and playback",
    "editor.audio": "Audio format",
    "editor.styles": "Custom styles",
    "label.entity_id": "Speakers",
    "label.recording_mode": "Recording mode",
    "label.selection_mode": "Speaker selection",
    "label.layout": "Layout",
    "label.microphone_icon": "Record icon",
    "label.speaker_icon": "Playback icon",
    "label.active_color": "Color",
    "label.show_timer": "Show timer and speaker name",
    "label.max_duration": "Maximum length",
    "label.min_duration": "Minimum length",
    "label.auto_play": "Play right away",
    "label.announce": "Announcement mode",
    "label.playback_start_delay": "Playback start delay",
    "label.input_profile": "Recording format",
    "label.output_profile": "Speaker profile",
    "label.transcoding": "Conversion",
    "label.input_mime_candidates": "Preferred recording formats",
    "label.transcode_codec": "Output codec",
    "label.transcode_bitrate": "Output bitrate",
    "label.transcode_sample_rate": "Output sample rate",
    "label.transcode_channels": "Output channels",
    "label.output_passthrough_rules": "Formats sent without conversion",
    "label.button_css": "Button CSS",
    "label.status_css": "Status text CSS",
    "label.timer_css": "Timer CSS",
    "label.text_css": "Text area CSS",
    "helper.entity_id": "Pick one speaker, or several to choose from right on the card.",
    "helper.max_duration": "Recording stops automatically at this length.",
    "helper.min_duration": "Shorter recordings are discarded, so accidental taps aren't sent.",
    "helper.auto_play": "Plays the announcement as soon as it's uploaded.",
    "helper.announce": "On speakers that support it, music is lowered during the announcement and resumes afterwards.",
    "helper.playback_start_delay": "How long the card waits before showing that it's playing. Match it to how long your speakers take to start.",
    "helper.input_profile": "Which recording format the browser tries first. This browser will record {mime}.",
    "helper.input_mime_candidates": "Overrides the recording format order. Leave empty to use the recording format above.",
    "helper.transcode": "Leave empty to use the speaker profile's default.",
    "helper.output_passthrough_rules": "YAML list of formats your speakers play as-is, for example “- mime_type: audio/mpeg”. Leave empty to use the speaker profile.",
    "helper.css": "CSS declarations only, without selectors. Only safe visual properties are applied.",
    "helper.browser_default": "in its default format",
    "option.hold": "Hold to talk",
    "option.hold.desc": "Records while you hold the button down.",
    "option.toggle": "Tap to start and stop",
    "option.toggle.desc": "Tap once to start and again to send.",
    "option.multiple": "Several at once",
    "option.multiple.desc": "Pick any combination of speakers, or all of them.",
    "option.single": "One at a time",
    "option.single.desc": "Picking a speaker replaces the previous one.",
    "option.horizontal": "Horizontal",
    "option.horizontal.desc": "Button beside the text, like a tile card.",
    "option.vertical": "Vertical",
    "option.vertical.desc": "Button above the text.",
    "input.default": "Automatic",
    "input.chrome": "Prefer MP4 (Chrome, Edge)",
    "input.safari": "Prefer MP4 (Safari, iOS)",
    "output.default": "Any speaker",
    "output.default.desc": "Converts every recording to MP3, which almost every speaker can play.",
    "output.homepod": "HomePod and AirPlay",
    "output.homepod.desc": "Sends MP3 as-is and converts everything else to MP3.",
    "output.google_home": "Google and Nest speakers",
    "output.google_home.desc": "Sends MP3 and AAC as-is and converts everything else to MP3.",
    "output.custom": "Custom",
    "output.custom.desc": "Uses only the formats and conversion settings you set below.",
    "transcoding.always": "Always convert",
    "transcoding.always.desc": "Every recording is converted with ffmpeg. The most compatible choice.",
    "transcoding.auto": "Only when needed",
    "transcoding.auto.desc": "Skips conversion when the speaker profile accepts the recorded format, so playback starts sooner.",
    "transcoding.never": "Never convert",
    "transcoding.never.desc": "Nothing is converted. Recordings the speaker profile doesn't accept are rejected.",
    "channels.1": "Mono",
    "channels.2": "Stereo",
  },
  es: {
    "card.hold": "Mantén para hablar",
    "card.toggle": "Toca para hablar",
    "card.choose_target": "Elige un altavoz",
    "card.starting": "Preparando…",
    "card.release": "Suelta para enviar",
    "card.tap_send": "Toca para enviar",
    "card.finishing": "Terminando…",
    "card.sending": "Enviando…",
    "card.starting_playback": "Iniciando reproducción…",
    "card.playing": "Reproduciendo en {target}",
    "card.sent": "Enviado",
    "card.speakers": "{count} altavoces",
    "card.all": "Todos",
    "card.aria": "Grabar un anuncio de voz",
    "card.targets_aria": "Altavoces",
    "error.unsupported": "Este navegador no puede grabar audio",
    "error.insecure": "El micrófono requiere HTTPS",
    "error.mic_denied": "Se denegó el acceso al micrófono",
    "error.no_mic": "No se encontró un micrófono",
    "error.start": "No se pudo iniciar la grabación",
    "error.stop": "No se pudo detener la grabación",
    "error.too_short": "Grabación demasiado corta",
    "error.empty": "La grabación está vacía",
    "error.send": "No se pudo enviar el anuncio",
    "error.no_api": "Home Assistant no está conectado",
    "editor.appearance": "Apariencia",
    "editor.recording": "Grabación y reproducción",
    "editor.audio": "Formato de audio",
    "editor.styles": "Estilos personalizados",
    "label.entity_id": "Altavoces",
    "label.recording_mode": "Modo de grabación",
    "label.selection_mode": "Selección de altavoces",
    "label.layout": "Diseño",
    "label.microphone_icon": "Icono de grabación",
    "label.speaker_icon": "Icono de reproducción",
    "label.active_color": "Color",
    "label.show_timer": "Mostrar temporizador y altavoz",
    "label.max_duration": "Duración máxima",
    "label.min_duration": "Duración mínima",
    "label.auto_play": "Reproducir de inmediato",
    "label.announce": "Modo anuncio",
    "label.playback_start_delay": "Retardo de inicio de reproducción",
    "label.input_profile": "Formato de grabación",
    "label.output_profile": "Perfil de altavoz",
    "label.transcoding": "Conversión",
    "label.input_mime_candidates": "Formatos de grabación preferidos",
    "label.transcode_codec": "Códec de salida",
    "label.transcode_bitrate": "Bitrate de salida",
    "label.transcode_sample_rate": "Muestreo de salida",
    "label.transcode_channels": "Canales de salida",
    "label.output_passthrough_rules": "Formatos enviados sin convertir",
    "label.button_css": "CSS del botón",
    "label.status_css": "CSS del texto de estado",
    "label.timer_css": "CSS del temporizador",
    "label.text_css": "CSS de la zona de texto",
    "helper.entity_id": "Elige un altavoz, o varios para escoger directamente desde la tarjeta.",
    "helper.max_duration": "La grabación se detiene sola al llegar a esta duración.",
    "helper.min_duration": "Las grabaciones más cortas se descartan, así no se envían toques accidentales.",
    "helper.auto_play": "Reproduce el anuncio apenas termina de subirse.",
    "helper.announce": "En los altavoces compatibles, la música baja durante el anuncio y luego continúa.",
    "helper.playback_start_delay": "Cuánto espera la tarjeta antes de indicar que está reproduciendo. Ajústalo a lo que tardan tus altavoces en empezar.",
    "helper.input_profile": "Qué formato de grabación intenta primero el navegador. Este navegador grabará {mime}.",
    "helper.input_mime_candidates": "Reemplaza el orden de formatos de grabación. Déjalo vacío para usar el formato de grabación de arriba.",
    "helper.transcode": "Déjalo vacío para usar el valor del perfil de altavoz.",
    "helper.output_passthrough_rules": "Lista YAML de formatos que tus altavoces reproducen tal cual, por ejemplo “- mime_type: audio/mpeg”. Déjalo vacío para usar el perfil de altavoz.",
    "helper.css": "Solo declaraciones CSS, sin selectores. Únicamente se aplican propiedades visuales seguras.",
    "helper.browser_default": "en su formato por defecto",
    "option.hold": "Mantener para hablar",
    "option.hold.desc": "Graba mientras mantienes presionado el botón.",
    "option.toggle": "Tocar para iniciar y detener",
    "option.toggle.desc": "Toca una vez para empezar y otra para enviar.",
    "option.multiple": "Varios a la vez",
    "option.multiple.desc": "Elige cualquier combinación de altavoces, o todos.",
    "option.single": "Uno a la vez",
    "option.single.desc": "Al elegir un altavoz se reemplaza el anterior.",
    "option.horizontal": "Horizontal",
    "option.horizontal.desc": "Botón junto al texto, como una tarjeta tile.",
    "option.vertical": "Vertical",
    "option.vertical.desc": "Botón sobre el texto.",
    "input.default": "Automático",
    "input.chrome": "Preferir MP4 (Chrome, Edge)",
    "input.safari": "Preferir MP4 (Safari, iOS)",
    "output.default": "Cualquier altavoz",
    "output.default.desc": "Convierte cada grabación a MP3, que casi cualquier altavoz puede reproducir.",
    "output.homepod": "HomePod y AirPlay",
    "output.homepod.desc": "Envía MP3 tal cual y convierte todo lo demás a MP3.",
    "output.google_home": "Altavoces Google y Nest",
    "output.google_home.desc": "Envía MP3 y AAC tal cual y convierte todo lo demás a MP3.",
    "output.custom": "Personalizado",
    "output.custom.desc": "Usa solo los formatos y ajustes de conversión que definas abajo.",
    "transcoding.always": "Convertir siempre",
    "transcoding.always.desc": "Cada grabación se convierte con ffmpeg. La opción más compatible.",
    "transcoding.auto": "Solo si hace falta",
    "transcoding.auto.desc": "Evita la conversión cuando el perfil de altavoz acepta el formato grabado, así la reproducción empieza antes.",
    "transcoding.never": "Nunca convertir",
    "transcoding.never.desc": "No se convierte nada. Las grabaciones que el perfil de altavoz no acepta se rechazan.",
    "channels.1": "Mono",
    "channels.2": "Estéreo",
  },
};

function localize(hass, key, vars = {}) {
  const language = String(hass?.locale?.language || hass?.language || "en").split("-")[0];
  const template = STRINGS[language]?.[key] ?? STRINGS.en[key] ?? key;
  return template.replace(/\{(\w+)\}/g, (_match, name) => String(vars[name] ?? ""));
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isStringArray(value) {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function getTargets(config) {
  const raw = Array.isArray(config?.entity_id) ? config.entity_id : [config?.entity_id];
  return [...new Set(raw.filter((item) => typeof item === "string" && item.trim()))];
}

function normalizeIconName(value) {
  const icon = String(value || "").trim();
  return /^[a-z0-9_-]+:[a-z0-9_.-]+$/i.test(icon) ? icon : "";
}

function isValidColor(value) {
  return /^(#[0-9a-f]{3}|#[0-9a-f]{6}|[a-z][a-z-]*)$/i.test(String(value || "").trim());
}

function computeCssColor(value) {
  const color = String(value || "").trim();
  if (!isValidColor(color)) {
    return "var(--red-color)";
  }
  return color.startsWith("#") ? color : `var(--${color.toLowerCase()}-color)`;
}

function sanitizeInlineCss(cssText, allowedProperties) {
  const rawCss = String(cssText || "")
    .replace(/\/\*[\s\S]*?\*\//g, " ")
    .slice(0, MAX_CUSTOM_CSS_LENGTH);
  const declarations = [];
  for (const chunk of rawCss.split(";")) {
    const separatorIndex = chunk.indexOf(":");
    if (separatorIndex <= 0) {
      continue;
    }
    const property = chunk.slice(0, separatorIndex).trim().toLowerCase();
    const value = chunk.slice(separatorIndex + 1).trim();
    const allowed =
      allowedProperties.has(property) || property.startsWith("--voice-announcement-");
    if (
      !value ||
      !allowed ||
      BLOCKED_INLINE_CSS_PATTERN.test(property) ||
      BLOCKED_INLINE_CSS_PATTERN.test(value)
    ) {
      continue;
    }
    const style = document.createElement("div").style;
    style.setProperty(property, value);
    const normalizedValue = style.getPropertyValue(property).trim();
    if (normalizedValue && !BLOCKED_INLINE_CSS_PATTERN.test(normalizedValue)) {
      declarations.push(`${property}: ${normalizedValue}`);
    }
  }
  return declarations.join("; ");
}

function getInputMimeCandidates(config) {
  if (Array.isArray(config?.input_mime_candidates) && config.input_mime_candidates.length) {
    return config.input_mime_candidates.map((item) => String(item).trim()).filter(Boolean);
  }
  return [...(INPUT_PROFILES[config?.input_profile] || INPUT_PROFILES.default)];
}

function pickSupportedMimeType(candidates) {
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) {
    return "";
  }
  return (
    candidates.find((mimeType) => {
      try {
        return MediaRecorder.isTypeSupported(mimeType);
      } catch (_err) {
        return false;
      }
    }) || ""
  );
}

function hasUserMediaSupport() {
  return Boolean(
    navigator.mediaDevices?.getUserMedia ||
      navigator.getUserMedia ||
      navigator.webkitGetUserMedia ||
      navigator.mozGetUserMedia
  );
}

function getDefaultEntityId(hass) {
  return Object.keys(hass?.states || {}).find((entityId) => entityId.startsWith("media_player.")) || "";
}

function readStorage(key) {
  try {
    return JSON.parse(window.localStorage.getItem(key) || "null");
  } catch (_err) {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (_err) {
    // Storage can be unavailable in private windows or embedded webviews.
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function yieldToUi() {
  return new Promise((resolve) => {
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(() => resolve());
      return;
    }
    window.setTimeout(resolve, 0);
  });
}

async function withTimeout(promise, timeoutMs, label, onTimeout) {
  let timeout;
  const guardedPromise = Promise.resolve(promise);
  const timeoutPromise = new Promise((_resolve, reject) => {
    timeout = window.setTimeout(() => {
      onTimeout?.();
      reject(new Error(`${label} timed out after ${timeoutMs}ms`));
    }, timeoutMs);
  });
  try {
    return await Promise.race([guardedPromise, timeoutPromise]);
  } finally {
    window.clearTimeout(timeout);
    guardedPromise.catch(() => undefined);
  }
}

const BUTTON_STYLES = `
  .record-button {
    align-items: center;
    appearance: none;
    aspect-ratio: 1;
    background-color: var(
      --voice-announcement-button-color,
      color-mix(in srgb, var(--voice-announcement-active-color) 20%, transparent)
    );
    background-image: var(--voice-announcement-button-image, none);
    background-position: center;
    background-repeat: no-repeat;
    background-size: cover;
    border: var(--voice-announcement-button-border, 0);
    border-radius: var(--voice-announcement-button-border-radius, 50%);
    box-shadow: var(--voice-announcement-button-shadow, none);
    color: var(--voice-announcement-button-icon-color, var(--voice-announcement-active-color));
    cursor: pointer;
    display: inline-grid;
    isolation: isolate;
    outline: none;
    overflow: hidden;
    padding: 0;
    place-items: center;
    position: relative;
    touch-action: none;
    transition:
      background-color 140ms ease,
      box-shadow 140ms ease,
      color 140ms ease,
      opacity 140ms ease,
      transform 140ms ease;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
    -webkit-touch-callout: none;
  }

  .record-button:focus-visible {
    box-shadow: var(
      --voice-announcement-button-focus-shadow,
      0 0 0 2px var(--voice-announcement-active-color)
    );
  }

  .record-button.recording,
  .record-button.uploading,
  .record-button.playing {
    background-color: var(
      --voice-announcement-button-color-recording,
      var(--voice-announcement-active-color)
    );
    color: var(--voice-announcement-button-icon-color-active, #fff);
  }

  .record-button.recording {
    animation: var(
      --voice-announcement-button-recording-animation,
      voice-announcement-pulse 1.15s ease-in-out infinite
    );
    transform: scale(0.96);
  }

  .record-button.uploading {
    cursor: wait;
    opacity: 0.9;
  }

  .record-button.playing {
    cursor: progress;
    opacity: 0.94;
  }

  .record-button:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .center-pulse {
    background: var(
      --voice-announcement-center-pulse-background,
      radial-gradient(
        circle at center,
        var(--voice-announcement-center-pulse-color, rgba(255, 255, 255, 0.34)) 0%,
        var(--voice-announcement-center-pulse-color, rgba(255, 255, 255, 0.34)) 28%,
        transparent 72%
      )
    );
    border-radius: inherit;
    display: none;
    inset: var(--voice-announcement-center-pulse-inset, 0);
    pointer-events: none;
    position: absolute;
    transform: scale(var(--voice-announcement-center-pulse-scale-min, 0.24));
    z-index: 0;
  }

  .record-button.recording .center-pulse {
    animation: voice-announcement-center-pulse
      var(--voice-announcement-center-pulse-duration, 1400ms) ease-in-out infinite;
    display: var(--voice-announcement-center-pulse-display-recording, block);
  }

  .record-button ha-icon {
    pointer-events: none;
    position: relative;
    z-index: 1;
  }

  @keyframes voice-announcement-pulse {
    0% {
      box-shadow: 0 0 0 0
        color-mix(in srgb, var(--voice-announcement-active-color) 46%, transparent);
    }
    70% {
      box-shadow: 0 0 0 var(--voice-announcement-pulse-size, 14px)
        color-mix(in srgb, var(--voice-announcement-active-color) 0%, transparent);
    }
    100% {
      box-shadow: 0 0 0 0
        color-mix(in srgb, var(--voice-announcement-active-color) 0%, transparent);
    }
  }

  @keyframes voice-announcement-center-pulse {
    0% {
      opacity: 0;
      transform: scale(var(--voice-announcement-center-pulse-scale-min, 0.24));
    }
    42% {
      opacity: var(--voice-announcement-center-pulse-opacity, 0.36);
    }
    100% {
      opacity: 0;
      transform: scale(var(--voice-announcement-center-pulse-scale-max, 1.18));
    }
  }
`;

class VoiceAnnouncementCard extends HTMLElement {
  static async getConfigElement() {
    await customElements.whenDefined(EDITOR_TAG);
    return document.createElement(EDITOR_TAG);
  }

  static getStubConfig(hass) {
    return {
      type: `custom:${VOICE_ANNOUNCEMENT_TAG}`,
      entity_id: getDefaultEntityId(hass),
    };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = undefined;
    this._hass = undefined;
    this._targets = [];
    this._selected = [];
    this._state = "idle";
    this._status = "";
    this._timerText = "00:00";
    this._targetsSignature = "";
    this._chunks = [];
    this._recorder = undefined;
    this._stream = undefined;
    this._audioContext = undefined;
    this._sourceNode = undefined;
    this._processorNode = undefined;
    this._silentGainNode = undefined;
    this._fallbackBuffers = [];
    this._fallbackSampleRate = 0;
    this._fallbackLength = 0;
    this._startedAt = 0;
    this._timer = undefined;
    this._maxTimer = undefined;
    this._errorTimer = undefined;
    this._stopPromise = undefined;
    this._startPromise = undefined;
    this._stopAfterStart = false;
  }

  setConfig(config) {
    this._validateConfig(config);
    this._config = { ...DEFAULT_CONFIG, ...config };
    this._targets = getTargets(config);
    const stored = this._hasPicker() ? readStorage(this._storageKey()) : null;
    const remembered = Array.isArray(stored)
      ? stored.filter((entityId) => this._targets.includes(entityId))
      : [];
    this._selected = this._hasPicker()
      ? stored === null
        ? [this._targets[0]]
        : remembered.slice(0, this._isSingleSelect() ? 1 : undefined)
      : [...this._targets];
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._updateUi();
  }

  getCardSize() {
    return (this._getLayout() === "vertical" ? 2 : 1) + (this._hasPicker() ? 1 : 0);
  }

  getGridOptions() {
    if (this._hasPicker()) {
      return { columns: 12, rows: "auto", min_columns: 6 };
    }
    const isVertical = this._getLayout() === "vertical";
    return {
      columns: 6,
      rows: isVertical ? 2 : 1,
      min_columns: 3,
      min_rows: isVertical ? 2 : 1,
    };
  }

  connectedCallback() {
    this._updateUi();
  }

  disconnectedCallback() {
    this._clearTimers();
    window.clearTimeout(this._errorTimer);
    this._cleanupAudioGraph();
    this._stopTracks();
  }

  _t(key, vars) {
    return localize(this._hass, key, vars);
  }

  _getLayout() {
    return this._config?.layout === "vertical" ? "vertical" : "horizontal";
  }

  _hasPicker() {
    return this._targets.length > 1;
  }

  _isSingleSelect() {
    return this._config?.selection_mode === "single";
  }

  _storageKey() {
    return `voice-announcement-targets:${this._config.selection_mode}:${this._targets.join(",")}`;
  }

  _validateConfig(config) {
    if (!isPlainObject(config)) {
      throw new Error("Invalid card configuration");
    }
    const targets = getTargets(config);
    if (!targets.length || targets.some((entityId) => !entityId.startsWith("media_player."))) {
      throw new Error("entity_id is required and must list media_player entities");
    }
    if (targets.length > MAX_TARGETS) {
      throw new Error(`entity_id supports up to ${MAX_TARGETS} media players`);
    }
    const choices = {
      recording_mode: RECORDING_MODES,
      selection_mode: SELECTION_MODES,
      layout: CARD_LAYOUTS,
      input_profile: Object.keys(INPUT_PROFILES),
      output_profile: OUTPUT_PROFILES,
      transcoding: TRANSCODING_MODES,
    };
    for (const [key, allowed] of Object.entries(choices)) {
      if (config[key] !== undefined && !allowed.includes(config[key])) {
        throw new Error(`${key} must be one of: ${allowed.join(", ")}`);
      }
    }
    for (const key of ["microphone_icon", "speaker_icon"]) {
      if (config[key] !== undefined && !normalizeIconName(config[key])) {
        throw new Error(`${key} must be an icon name, for example mdi:microphone`);
      }
    }
    if (config.active_color !== undefined && !isValidColor(config.active_color)) {
      throw new Error("active_color must be a Home Assistant color name or a hex color");
    }
    const maxDuration = Number(config.max_duration ?? DEFAULT_CONFIG.max_duration);
    const minDuration = Number(config.min_duration ?? DEFAULT_CONFIG.min_duration);
    const startDelay = Number(config.playback_start_delay ?? DEFAULT_CONFIG.playback_start_delay);
    if (!Number.isFinite(maxDuration) || maxDuration <= 0) {
      throw new Error("max_duration must be greater than zero");
    }
    if (!Number.isFinite(minDuration) || minDuration < 0 || maxDuration <= minDuration) {
      throw new Error("min_duration must be zero or more and lower than max_duration");
    }
    if (!Number.isFinite(startDelay) || startDelay < 0) {
      throw new Error("playback_start_delay must be zero or greater");
    }
    if (config.input_mime_candidates !== undefined && !isStringArray(config.input_mime_candidates)) {
      throw new Error("input_mime_candidates must be a list of MIME types");
    }
    if (config.output_passthrough_rules !== undefined && !Array.isArray(config.output_passthrough_rules)) {
      throw new Error("output_passthrough_rules must be a list");
    }
    if (config.transcode_target !== undefined && !isPlainObject(config.transcode_target)) {
      throw new Error("transcode_target must be an object");
    }
    for (const key of ["button_css", "status_css", "timer_css", "text_css"]) {
      if (config[key] !== undefined && typeof config[key] !== "string") {
        throw new Error(`${key} must be a string`);
      }
    }
  }

  _render() {
    const layout = this._getLayout();
    this.toggleAttribute("has-targets", this._hasPicker());
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
        }

        ha-card {
          box-sizing: border-box;
          height: 100%;
          overflow: hidden;
        }

        .container {
          align-items: center;
          box-sizing: border-box;
          display: grid;
          height: 100%;
          min-width: 0;
        }

        .layout-horizontal {
          gap: var(--voice-announcement-card-gap-horizontal, 10px);
          grid-template-columns:
            var(--voice-announcement-button-size-horizontal, 36px)
            minmax(0, 1fr);
          min-height: var(--voice-announcement-tile-min-height, 56px);
          padding: var(--voice-announcement-card-padding-horizontal, 10px);
        }

        .layout-vertical {
          gap: var(--voice-announcement-card-gap, 6px);
          grid-template-rows: minmax(0, 1fr) min-content;
          justify-items: center;
          padding: var(--voice-announcement-card-padding, 10px);
          text-align: center;
        }

        :host([has-targets]) .container {
          height: auto;
        }

        :host([has-targets]) .layout-vertical {
          grid-template-rows: auto auto;
        }

        .button-frame {
          display: grid;
          min-height: 0;
          min-width: 0;
          place-items: center;
        }

        .layout-vertical .button-frame {
          container-type: size;
          height: 100%;
          min-height: var(--voice-announcement-button-size, 72px);
          width: 100%;
        }

        :host([has-targets]) .layout-vertical .button-frame {
          container-type: normal;
          height: auto;
        }

        .record-button {
          width: var(--voice-announcement-button-size-horizontal, 36px);
        }

        .layout-vertical .record-button {
          width: min(var(--voice-announcement-button-size, 80cqh), 100cqw, 100cqh);
        }

        :host([has-targets]) .layout-vertical .record-button {
          width: var(--voice-announcement-button-size, 72px);
        }

        .record-button ha-icon {
          --mdc-icon-size: var(--voice-announcement-button-icon-size-horizontal, 24px);
        }

        .layout-vertical .record-button ha-icon {
          --mdc-icon-size: var(--voice-announcement-button-icon-size, 34cqmin);
        }

        :host([has-targets]) .layout-vertical .record-button ha-icon {
          --mdc-icon-size: var(--voice-announcement-button-icon-size, 32px);
        }

        ${BUTTON_STYLES}

        .text-zone {
          display: var(--voice-announcement-text-display, grid);
          gap: var(--voice-announcement-text-gap, 0);
          min-width: 0;
        }

        .status {
          color: var(--voice-announcement-label-color, var(--primary-text-color));
          font-size: var(--voice-announcement-label-font-size, var(--ha-font-size-m, 14px));
          font-weight: var(--voice-announcement-label-font-weight, var(--ha-font-weight-medium, 500));
          letter-spacing: 0.1px;
          line-height: var(--ha-line-height-condensed, 20px);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .timer {
          color: var(--voice-announcement-timer-color, var(--secondary-text-color));
          display: var(--voice-announcement-timer-display, block);
          font-size: var(--voice-announcement-timer-font-size, var(--ha-font-size-s, 12px));
          font-variant-numeric: tabular-nums;
          letter-spacing: 0.4px;
          line-height: var(--ha-line-height-condensed, 16px);
          min-height: 16px;
          overflow: hidden;
          text-overflow: ellipsis;
          visibility: var(--voice-announcement-timer-visibility, visible);
          white-space: nowrap;
        }

        :host([hide-timer]) .timer {
          display: none;
        }

        .targets {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          grid-column: 1 / -1;
          justify-content: var(--voice-announcement-targets-justify, flex-start);
        }

        .layout-vertical .targets {
          justify-content: var(--voice-announcement-targets-justify, center);
        }

        .target {
          align-items: center;
          background: transparent;
          border: 1px solid var(--outline-color, var(--divider-color));
          border-radius: var(--voice-announcement-chip-border-radius, 8px);
          box-sizing: border-box;
          color: var(--primary-text-color);
          cursor: pointer;
          display: inline-flex;
          font: inherit;
          font-size: var(--ha-font-size-s, 13px);
          font-weight: var(--ha-font-weight-medium, 500);
          gap: 6px;
          height: 32px;
          max-width: 100%;
          padding: 0 12px;
          transition: background-color 140ms ease, border-color 140ms ease;
        }

        .target span {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .target ha-icon {
          --mdc-icon-size: 18px;
          display: none;
          margin-inline-start: -4px;
        }

        .target[aria-pressed="true"] {
          background: color-mix(in srgb, var(--primary-color) 18%, transparent);
          border-color: transparent;
        }

        .target[aria-pressed="true"] ha-icon {
          display: inline-flex;
        }

        .target:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 1px;
        }

        .target:disabled {
          cursor: not-allowed;
          opacity: 0.5;
        }
      </style>
      <ha-card>
        <div class="container layout-${layout}" part="container">
          <div class="button-frame">
            <button class="record-button" part="button" type="button" aria-pressed="false">
              <span class="center-pulse" part="center-pulse" aria-hidden="true"></span>
              <ha-icon part="button-icon" icon="${DEFAULT_CONFIG.microphone_icon}"></ha-icon>
            </button>
          </div>
          <div class="text-zone" part="text">
            <div class="status" part="status" role="status"></div>
            <div class="timer" part="timer"></div>
          </div>
          ${this._hasPicker() ? `<div class="targets" part="targets" role="group"></div>` : ""}
        </div>
      </ha-card>
    `;

    this._button = this.shadowRoot.querySelector(".record-button");
    this._iconElement = this.shadowRoot.querySelector('[part="button-icon"]');
    this._textElement = this.shadowRoot.querySelector(".text-zone");
    this._statusElement = this.shadowRoot.querySelector(".status");
    this._timerElement = this.shadowRoot.querySelector(".timer");
    this._targetsElement = this.shadowRoot.querySelector(".targets");
    this._targetsSignature = "";
    this._applyStyles();
    this._attachHandlers();
    this._updateUi();
  }

  _attachHandlers() {
    const button = this._button;
    button.addEventListener("click", (event) => this._onClick(event));
    button.addEventListener("pointerdown", (event) => this._onPointerDown(event));
    button.addEventListener("pointerup", () => this._onHoldEnd());
    button.addEventListener("pointercancel", () => this._onHoldEnd());
    button.addEventListener("keydown", (event) => this._onKey(event, true));
    button.addEventListener("keyup", (event) => this._onKey(event, false));
    button.addEventListener("blur", () => this._onHoldEnd());
    button.addEventListener("contextmenu", (event) => event.preventDefault());
    this._targetsElement?.addEventListener("click", (event) => {
      const chip = event.target.closest("[data-target]");
      if (chip && !chip.disabled) {
        this._toggleTarget(chip.dataset.target);
      }
    });
  }

  _toggleTarget(entityId) {
    const available = this._targets.filter((target) => this._isAvailable(target));
    if (entityId === "*") {
      const allSelected = available.every((target) => this._selected.includes(target));
      this._selected = allSelected ? [] : available;
    } else if (this._isSingleSelect()) {
      this._selected = [entityId];
    } else if (this._selected.includes(entityId)) {
      this._selected = this._selected.filter((target) => target !== entityId);
    } else {
      this._selected = this._targets.filter(
        (target) => target === entityId || this._selected.includes(target)
      );
    }
    writeStorage(this._storageKey(), this._selected);
    this._updateUi();
  }

  _isAvailable(entityId) {
    const state = this._hass?.states?.[entityId]?.state;
    return state !== undefined && state !== "unavailable";
  }

  _activeTargets() {
    return this._selected.filter((entityId) => this._isAvailable(entityId));
  }

  _targetName(entityId) {
    return this._hass?.states?.[entityId]?.attributes?.friendly_name || entityId;
  }

  _targetLabel() {
    const targets = this._activeTargets();
    if (targets.length > 2) {
      return this._t("card.speakers", { count: targets.length });
    }
    return targets.map((entityId) => this._targetName(entityId)).join(", ");
  }

  _isHoldMode() {
    return this._config.recording_mode !== "toggle";
  }

  async _onClick(event) {
    event.preventDefault();
    if (this._isHoldMode()) {
      return;
    }
    if (this._state === "recording") {
      await this._stopRecording();
      return;
    }
    await this._startRecording();
  }

  async _onPointerDown(event) {
    if (!this._isHoldMode() || event.button !== 0) {
      return;
    }
    event.preventDefault();
    try {
      this._button.setPointerCapture(event.pointerId);
    } catch (_err) {
      // Pointer capture is not guaranteed in every webview.
    }
    await this._startRecording();
  }

  async _onKey(event, pressed) {
    if (!this._isHoldMode() || (event.key !== " " && event.key !== "Enter")) {
      return;
    }
    event.preventDefault();
    if (!pressed) {
      await this._onHoldEnd();
    } else if (!event.repeat) {
      await this._startRecording();
    }
  }

  async _onHoldEnd() {
    if (!this._isHoldMode()) {
      return;
    }
    if (this._state === "starting") {
      this._stopAfterStart = true;
      await this._startPromise;
    }
    if (this._state === "recording") {
      await this._stopRecording();
    }
  }

  async _startRecording() {
    if (this._startPromise) {
      return this._startPromise;
    }
    if (["starting", "recording", "uploading", "playing"].includes(this._state)) {
      return undefined;
    }
    if (!this._activeTargets().length) {
      return undefined;
    }
    if (!hasUserMediaSupport()) {
      this._setError(this._t(window.isSecureContext === false ? "error.insecure" : "error.unsupported"));
      return undefined;
    }

    window.clearTimeout(this._errorTimer);
    this._stopAfterStart = false;
    this._setState("starting", "card.starting");
    this._startPromise = this._doStartRecording();
    try {
      await this._startPromise;
    } finally {
      this._startPromise = undefined;
    }
    return undefined;
  }

  async _doStartRecording() {
    try {
      const stream = await this._getAudioStream();
      if (!this.isConnected) {
        stream.getTracks().forEach((track) => track.stop());
        this._setState("idle");
        return;
      }

      this._stream = stream;
      this._chunks = [];
      this._startedAt = performance.now();
      await this._startBestRecorder(stream);
      this._setState("recording", this._isHoldMode() ? "card.release" : "card.tap_send");
      this._startTimers();
      if (this._stopAfterStart) {
        this._stopAfterStart = false;
        await this._stopRecording();
      }
    } catch (err) {
      this._cleanupAudioGraph();
      this._stopTracks();
      this._setError(this._formatError(err, "error.start"));
    }
  }

  async _stopRecording() {
    if (this._state !== "recording" || !this._recorder) {
      return;
    }

    const recorder = this._recorder;
    const stopPromise = this._stopPromise;
    const targets = this._activeTargets();
    this._clearTimers();
    this._setState("uploading", "card.finishing");
    await yieldToUi();

    try {
      try {
        if (recorder.state !== "inactive") {
          try {
            recorder.requestData?.();
          } catch (_err) {
            // Some WebViews throw while the recorder is already stopping.
          }
          recorder.stop();
        }
        if (stopPromise) {
          await withTimeout(stopPromise, RECORDING_STOP_TIMEOUT_MS, "MediaRecorder stop");
        }
      } catch (err) {
        this._setError(this._formatError(err, "error.stop"));
        return;
      } finally {
        this._cleanupAudioGraph();
        this._stopTracks();
      }

      const duration = (performance.now() - this._startedAt) / 1000;
      if (duration < Number(this._config.min_duration)) {
        this._setError(this._t("error.too_short"));
        return;
      }

      try {
        this._setState("uploading", "card.sending");
        await yieldToUi();
        const blob = await this._buildRecordingBlob(recorder);
        if (blob.size === 0) {
          throw new Error(this._t("error.empty"));
        }
        const result = await this._uploadRecording(blob, duration, targets);
        if (this._config.auto_play !== false) {
          this._setState("playing", "card.starting_playback");
          const playPromise = this._playRecording(result, targets);
          await this._awaitLikelyPlaybackStart(playPromise);
          const playbackStartedAt = performance.now();
          this._setState("playing", "card.playing");
          await playPromise;
          await this._holdPlaybackStatus(duration, playbackStartedAt);
          this._setState("idle");
        } else {
          this._flashStatus("card.sent");
        }
      } catch (err) {
        this._setError(this._formatError(err, "error.send"));
      }
    } finally {
      this._recorder = undefined;
      this._stopPromise = undefined;
      this._chunks = [];
      this._fallbackBuffers = [];
      this._fallbackLength = 0;
      this._timerText = "00:00";
      this._updateUi();
    }
  }

  async _getAudioStream() {
    const constraints = {
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 24000,
      },
    };
    try {
      return await this._requestUserMedia(constraints);
    } catch (err) {
      if (err?.name === "OverconstrainedError" || err?.name === "ConstraintNotSatisfiedError") {
        return this._requestUserMedia({ audio: true });
      }
      throw err;
    }
  }

  _requestUserMedia(constraints) {
    if (navigator.mediaDevices?.getUserMedia) {
      return navigator.mediaDevices.getUserMedia(constraints);
    }
    const legacyGetUserMedia =
      navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
    return new Promise((resolve, reject) => {
      legacyGetUserMedia.call(navigator, constraints, resolve, reject);
    });
  }

  async _startBestRecorder(stream) {
    if (typeof MediaRecorder !== "undefined") {
      try {
        this._startMediaRecorder(stream);
        return;
      } catch (err) {
        console.warn("Voice Announcement: MediaRecorder failed, using WAV fallback", err);
      }
    }
    await this._startWavFallbackRecorder(stream);
  }

  _startMediaRecorder(stream) {
    const mimeType = pickSupportedMimeType(getInputMimeCandidates(this._config));
    const recorder = new MediaRecorder(stream, {
      audioBitsPerSecond: AUDIO_BITS_PER_SECOND,
      ...(mimeType ? { mimeType } : {}),
    });
    this._recorder = recorder;
    this._stopPromise = new Promise((resolve, reject) => {
      recorder.onstop = resolve;
      recorder.onerror = (event) => reject(event.error || event);
    });
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this._chunks.push(event.data);
      }
    };
    recorder.start(RECORDING_TIMESLICE_MS);
  }

  async _startWavFallbackRecorder(stream) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
      throw new Error(this._t("error.unsupported"));
    }

    let audioContext;
    try {
      audioContext = new AudioContextClass({ sampleRate: FALLBACK_SAMPLE_RATE });
    } catch (_err) {
      audioContext = new AudioContextClass();
    }
    if (audioContext.state === "suspended") {
      await audioContext.resume();
    }

    const sourceNode = audioContext.createMediaStreamSource(stream);
    const processorNode = audioContext.createScriptProcessor(FALLBACK_BUFFER_SIZE, 1, 1);
    const silentGainNode = audioContext.createGain();
    silentGainNode.gain.value = 0;

    this._audioContext = audioContext;
    this._sourceNode = sourceNode;
    this._processorNode = processorNode;
    this._silentGainNode = silentGainNode;
    this._fallbackBuffers = [];
    this._fallbackSampleRate = audioContext.sampleRate;
    this._fallbackLength = 0;

    processorNode.onaudioprocess = (event) => {
      const copy = new Float32Array(event.inputBuffer.getChannelData(0));
      this._fallbackBuffers.push(copy);
      this._fallbackLength += copy.length;
    };

    sourceNode.connect(processorNode);
    processorNode.connect(silentGainNode);
    silentGainNode.connect(audioContext.destination);

    this._stopPromise = Promise.resolve();
    this._recorder = {
      mimeType: "audio/wav",
      state: "recording",
      stop() {
        this.state = "inactive";
      },
    };
  }

  _cleanupAudioGraph() {
    if (this._processorNode) {
      this._processorNode.onaudioprocess = null;
    }
    for (const node of [this._processorNode, this._sourceNode, this._silentGainNode]) {
      try {
        node?.disconnect();
      } catch (_err) {
        // Disconnect can throw if the node was already disconnected.
      }
    }
    this._processorNode = undefined;
    this._sourceNode = undefined;
    this._silentGainNode = undefined;
    if (this._audioContext && this._audioContext.state !== "closed") {
      this._audioContext.close?.().catch(() => undefined);
    }
    this._audioContext = undefined;
  }

  async _buildRecordingBlob(recorder) {
    if (recorder.mimeType === "audio/wav" && this._chunks.length === 0) {
      return this._createWavBlob(this._fallbackBuffers, this._fallbackLength, this._fallbackSampleRate);
    }
    const blobType = recorder.mimeType || this._chunks.find((chunk) => chunk.type)?.type || "";
    return new Blob(this._chunks, { type: blobType });
  }

  async _createWavBlob(buffers, totalLength, sampleRate) {
    const rate = sampleRate || 44100;
    const wavBuffer = new ArrayBuffer(44 + totalLength * 2);
    const view = new DataView(wavBuffer);
    const writeAscii = (offset, value) => {
      for (let index = 0; index < value.length; index += 1) {
        view.setUint8(offset + index, value.charCodeAt(index));
      }
    };

    writeAscii(0, "RIFF");
    view.setUint32(4, 36 + totalLength * 2, true);
    writeAscii(8, "WAVE");
    writeAscii(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, rate, true);
    view.setUint32(28, rate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeAscii(36, "data");
    view.setUint32(40, totalLength * 2, true);

    let offset = 44;
    let lastYield = performance.now();
    for (const buffer of buffers) {
      for (let index = 0; index < buffer.length; index += 1) {
        const sample = Math.max(-1, Math.min(1, buffer[index]));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
        offset += 2;
      }
      if (performance.now() - lastYield > 12) {
        await yieldToUi();
        lastYield = performance.now();
      }
    }
    return new Blob([wavBuffer], { type: "audio/wav" });
  }

  async _holdPlaybackStatus(duration, playbackStartedAt) {
    const targetMs = Math.max(PLAYBACK_STATUS_MIN_MS, duration * 1000 + PLAYBACK_STATUS_PADDING_MS);
    const remainingMs = targetMs - (performance.now() - playbackStartedAt);
    if (remainingMs > 0) {
      await sleep(remainingMs);
    }
  }

  async _awaitLikelyPlaybackStart(playPromise) {
    const delayMs = Math.max(0, Number(this._config.playback_start_delay) * 1000);
    // Waits for both, so the "playing" status reflects the speaker's start-up delay.
    await Promise.all([sleep(delayMs), playPromise]);
  }

  async _uploadRecording(blob, duration, targets) {
    const mimeType = blob.type || "application/octet-stream";
    const formData = new FormData();
    formData.append("file", blob, `announcement.${this._extensionForMime(mimeType)}`);
    formData.append("entity_id", targets.join(","));
    formData.append("mime_type", mimeType);
    formData.append("duration", String(duration));
    formData.append("payload_version", "3");
    formData.append("audio_policy", JSON.stringify(this._buildAudioPolicy()));

    const controller = new AbortController();
    const options = { method: "POST", body: formData, signal: controller.signal };
    const request = this._hass?.fetchWithAuth
      ? this._hass.fetchWithAuth("/api/voice_announcement/upload", options)
      : fetch("/api/voice_announcement/upload", { credentials: "same-origin", ...options });
    const response = await withTimeout(request, UPLOAD_TIMEOUT_MS, "Upload request", () =>
      controller.abort()
    );
    if (!response.ok) {
      const detail = await withTimeout(response.text(), RESPONSE_BODY_TIMEOUT_MS, "Upload error");
      throw new Error(detail.trim().slice(0, MAX_ERROR_LENGTH) || response.statusText);
    }
    return withTimeout(response.json(), RESPONSE_BODY_TIMEOUT_MS, "Upload response");
  }

  async _playRecording(result, targets) {
    if (typeof this._hass?.callService !== "function") {
      throw new Error(this._t("error.no_api"));
    }
    // One call per speaker so announce mode is only requested where it is supported.
    await Promise.all(
      targets.map((entityId) => {
        const features = Number(this._hass.states[entityId]?.attributes?.supported_features) || 0;
        const announce = this._config.announce !== false && (features & MEDIA_ANNOUNCE_FEATURE) !== 0;
        return this._hass.callService("media_player", "play_media", {
          entity_id: entityId,
          media_content_id: result.media_source_id,
          media_content_type: result.media_content_type || "music",
          ...(announce ? { announce: true } : {}),
        });
      })
    );
  }

  _extensionForMime(mimeType) {
    const extensions = {
      "audio/mp4": "m4a",
      "audio/x-m4a": "m4a",
      "audio/ogg": "ogg",
      "audio/wav": "wav",
      "audio/mpeg": "mp3",
      "audio/mp3": "mp3",
      "audio/webm": "webm",
    };
    return extensions[String(mimeType || "").split(";")[0].toLowerCase()] || "bin";
  }

  _buildAudioPolicy() {
    const config = this._config;
    const policy = {
      input_profile: config.input_profile,
      output_profile: config.output_profile,
      transcoding: config.transcoding,
      input_mime_candidates: getInputMimeCandidates(config),
    };
    if (Array.isArray(config.output_passthrough_rules)) {
      policy.output_passthrough_rules = config.output_passthrough_rules.filter(isPlainObject);
    }
    if (isPlainObject(config.transcode_target)) {
      policy.transcode_target = { ...config.transcode_target };
    }
    return policy;
  }

  _startTimers() {
    this._clearTimers();
    this._updateTimer();
    this._timer = window.setInterval(() => this._updateTimer(), 250);
    this._maxTimer = window.setTimeout(
      () => this._stopRecording(),
      Number(this._config.max_duration) * 1000
    );
  }

  _clearTimers() {
    window.clearInterval(this._timer);
    window.clearTimeout(this._maxTimer);
    this._timer = undefined;
    this._maxTimer = undefined;
  }

  _updateTimer() {
    const elapsed = Math.max(0, (performance.now() - this._startedAt) / 1000);
    const format = (seconds) =>
      `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
    this._timerText = `${format(elapsed)} / ${format(Number(this._config.max_duration))}`;
    this._updateUi();
  }

  _stopTracks() {
    this._stream?.getTracks().forEach((track) => track.stop());
    this._stream = undefined;
  }

  _setState(state, statusKey) {
    this._state = state;
    this._status = statusKey ? this._t(statusKey, { target: this._targetLabel() }) : "";
    this._updateUi();
  }

  _setError(message) {
    this._state = "error";
    this._status = message;
    this._updateUi();
    this._scheduleIdle();
  }

  _flashStatus(statusKey) {
    this._setState("done", statusKey);
    this._scheduleIdle();
  }

  _scheduleIdle() {
    window.clearTimeout(this._errorTimer);
    this._errorTimer = window.setTimeout(() => {
      if (this._state === "error" || this._state === "done") {
        this._setState("idle");
      }
    }, ERROR_STATUS_MS);
  }

  _formatError(err, fallbackKey) {
    if (err?.name === "NotAllowedError") {
      return this._t("error.mic_denied");
    }
    if (err?.name === "NotFoundError") {
      return this._t("error.no_mic");
    }
    return err?.message || this._t(fallbackKey);
  }

  _idleStatus() {
    if (!this._activeTargets().length) {
      return this._t("card.choose_target");
    }
    return this._t(this._isHoldMode() ? "card.hold" : "card.toggle");
  }

  _updateUi() {
    if (!this._button || !this._config) {
      return;
    }
    const busy = ["starting", "uploading", "playing"].includes(this._state);
    const isIdle = this._state === "idle" || this._state === "error" || this._state === "done";
    const showsTimer = this._state === "recording" || (this._state === "uploading" && this._timerText !== "00:00");
    const status = this._state === "idle" ? this._idleStatus() : this._status;

    this._button.classList.toggle("recording", this._state === "recording");
    this._button.classList.toggle("uploading", this._state === "uploading" || this._state === "starting");
    this._button.classList.toggle("playing", this._state === "playing");
    this._button.disabled = busy || !this._hass || (isIdle && !this._activeTargets().length);
    this._button.setAttribute("aria-pressed", String(this._state === "recording"));
    this._button.setAttribute("aria-label", `${this._t("card.aria")}: ${status}`);
    this._button.title = status;
    const icon = this._state === "uploading" || this._state === "playing"
      ? normalizeIconName(this._config.speaker_icon) || DEFAULT_CONFIG.speaker_icon
      : normalizeIconName(this._config.microphone_icon) || DEFAULT_CONFIG.microphone_icon;
    if (this._iconElement.getAttribute("icon") !== icon) {
      this._iconElement.setAttribute("icon", icon);
    }
    this._statusElement.textContent = status;
    this._timerElement.textContent = showsTimer ? this._timerText : this._targetLabel();
    this.toggleAttribute("hide-timer", this._config.show_timer === false);
    this._updateTargets(isIdle);
  }

  _updateTargets(enabled) {
    if (!this._targetsElement) {
      return;
    }
    const available = this._targets.filter((entityId) => this._isAvailable(entityId));
    const allChip = {
      id: "*",
      name: this._t("card.all"),
      pressed: available.length > 0 && available.every((entityId) => this._selected.includes(entityId)),
      disabled: !available.length,
    };
    const chips = [
      ...(this._isSingleSelect() ? [] : [allChip]),
      ...this._targets.map((entityId) => ({
        id: entityId,
        name: this._targetName(entityId),
        pressed: this._selected.includes(entityId) && this._isAvailable(entityId),
        disabled: !this._isAvailable(entityId),
      })),
    ];
    // Rebuild only when names change, so toggling a chip keeps keyboard focus.
    const signature = JSON.stringify(chips.map((chip) => chip.name));
    if (signature !== this._targetsSignature) {
      this._targetsSignature = signature;
      this._targetsElement.setAttribute("aria-label", this._t("card.targets_aria"));
      this._targetsElement.innerHTML = chips
        .map(
          (chip) => `
            <button class="target" part="target" type="button" data-target="${escapeHtml(chip.id)}">
              <ha-icon icon="mdi:check"></ha-icon><span>${escapeHtml(chip.name)}</span>
            </button>`
        )
        .join("");
    }
    this._targetsElement.querySelectorAll("[data-target]").forEach((element, index) => {
      element.setAttribute("aria-pressed", String(chips[index].pressed));
      element.disabled = chips[index].disabled || !enabled;
    });
  }

  _applyStyles() {
    this.style.setProperty("--voice-announcement-active-color", computeCssColor(this._config.active_color));
    const styles = [
      [this._button, this._config.button_css, SAFE_BUTTON_CSS_PROPERTIES],
      [this._statusElement, this._config.status_css, SAFE_STATUS_CSS_PROPERTIES],
      [this._timerElement, this._config.timer_css, SAFE_STATUS_CSS_PROPERTIES],
      [this._textElement, this._config.text_css, SAFE_TEXT_CSS_PROPERTIES],
    ];
    for (const [element, css, allowed] of styles) {
      if (element) {
        element.style.cssText = sanitizeInlineCss(css, allowed);
      }
    }
  }
}

class VoiceAnnouncementBadge extends VoiceAnnouncementCard {
  static getStubConfig(hass) {
    return {
      type: `custom:${VOICE_ANNOUNCEMENT_BADGE_TAG}`,
      entity_id: getDefaultEntityId(hass),
    };
  }

  getCardSize() {
    return 1;
  }

  _hasPicker() {
    return false;
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: inline-flex;
          vertical-align: middle;
          --voice-announcement-button-color: var(
            --voice-announcement-badge-color,
            var(--ha-card-background, var(--card-background-color, #fff))
          );
          --voice-announcement-button-color-recording: var(
            --voice-announcement-badge-color-recording,
            var(--voice-announcement-active-color)
          );
          --voice-announcement-button-icon-color: var(
            --voice-announcement-badge-icon-color,
            var(--voice-announcement-active-color)
          );
          --voice-announcement-pulse-size: 10px;
        }

        ${BUTTON_STYLES}

        .record-button {
          border: var(
            --voice-announcement-badge-border,
            var(--ha-card-border-width, 1px) solid var(--ha-card-border-color, var(--divider-color, #e0e0e0))
          );
          border-radius: var(--voice-announcement-badge-border-radius, var(--ha-badge-border-radius, 18px));
          box-shadow: var(--voice-announcement-badge-shadow, var(--ha-card-box-shadow, none));
          box-sizing: border-box;
          width: var(--voice-announcement-badge-size, var(--ha-badge-size, 36px));
        }

        .record-button ha-icon {
          --mdc-icon-size: var(--voice-announcement-badge-icon-size, var(--ha-badge-icon-size, 18px));
        }
      </style>
      <button class="record-button" part="badge button" type="button" aria-pressed="false">
        <span class="center-pulse" part="center-pulse" aria-hidden="true"></span>
        <ha-icon part="badge-icon button-icon" icon="${DEFAULT_CONFIG.microphone_icon}"></ha-icon>
      </button>
      <span hidden part="status"></span>
      <span hidden part="timer"></span>
    `;

    this._button = this.shadowRoot.querySelector(".record-button");
    this._iconElement = this.shadowRoot.querySelector("ha-icon");
    this._statusElement = this.shadowRoot.querySelector('[part="status"]');
    this._timerElement = this.shadowRoot.querySelector('[part="timer"]');
    this._textElement = undefined;
    this._targetsElement = undefined;
    this._applyStyles();
    this._attachHandlers();
    this._updateUi();
  }

  _updateUi() {
    super._updateUi();
    if (this._button && this._state === "recording") {
      this._button.title = `${this._status} ${this._timerText}`;
    }
  }
}

class VoiceAnnouncementCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._config = undefined;
    this._form = undefined;
    this._language = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._form) {
      this._render();
      return;
    }
    this._form.hass = hass;
    if (hass?.locale?.language !== this._language) {
      this._language = hass?.locale?.language;
      this._form.schema = this._schema();
    }
  }

  setConfig(config) {
    this._config = { ...config };
    if (this._form) {
      this._form.schema = this._schema();
      this._form.data = this._formData();
    } else {
      this._render();
    }
  }

  async _render() {
    if (!this._hass || !this._config || this._form) {
      return;
    }
    await this._ensureFormLoaded();
    if (this._form) {
      return;
    }
    const form = document.createElement("ha-form");
    form.computeLabel = (schema) => this._computeLabel(schema);
    form.computeHelper = (schema) => this._computeHelper(schema);
    form.addEventListener("value-changed", (event) => this._valueChanged(event.detail.value));
    form.hass = this._hass;
    form.schema = this._schema();
    form.data = this._formData();
    this._language = this._hass.locale?.language;
    this._form = form;
    this.shadowRoot.replaceChildren(form);
  }

  async _ensureFormLoaded() {
    if (customElements.get("ha-form")) {
      return;
    }
    // ha-form is lazy-loaded by Home Assistant; loading a built-in card editor registers it.
    const helpers = await window.loadCardHelpers?.();
    const card = await helpers?.createCardElement({ type: "entities", entities: [] });
    await card?.constructor?.getConfigElement?.();
    await customElements.whenDefined("ha-form");
  }

  _t(key, vars) {
    return localize(this._hass, key, vars);
  }

  _isBadge() {
    return this._config?.type === `custom:${VOICE_ANNOUNCEMENT_BADGE_TAG}`;
  }

  _options(values, prefix, withDescription = false) {
    return values.map((value) => ({
      value,
      label: this._t(`${prefix}${value}`),
      ...(withDescription ? { description: this._t(`${prefix}${value}.desc`) } : {}),
    }));
  }

  _schema() {
    const isBadge = this._isBadge();
    const cardOnly = (fields) => (isBadge ? [] : fields);
    const number = (min, max, step) => ({
      number: { mode: "box", min, max, step, unit_of_measurement: "s" },
    });
    const css = (name) => ({ name, selector: { text: { multiline: true } } });
    const transcodeField = (name) => ({
      name,
      selector: {
        select: {
          mode: "dropdown",
          options: TRANSCODE_FIELDS[name].options.map((value) => ({
            value,
            label: name === "transcode_channels" ? this._t(`channels.${value}`) : value.toUpperCase(),
          })),
        },
      },
    });

    return [
      {
        name: "entity_id",
        required: true,
        selector: { entity: { multiple: true, filter: [{ domain: "media_player" }] } },
      },
      {
        name: "recording_mode",
        selector: { select: { mode: "box", options: this._options(RECORDING_MODES, "option.", true) } },
      },
      ...cardOnly(
        getTargets(this._config).length > 1
          ? [
              {
                name: "selection_mode",
                selector: {
                  select: { mode: "box", options: this._options(SELECTION_MODES, "option.", true) },
                },
              },
            ]
          : []
      ),
      {
        name: "appearance",
        type: "expandable",
        flatten: true,
        icon: "mdi:palette-outline",
        schema: [
          ...cardOnly([
            {
              name: "layout",
              selector: { select: { mode: "box", options: this._options(CARD_LAYOUTS, "option.", true) } },
            },
          ]),
          {
            name: "",
            type: "grid",
            schema: [
              { name: "microphone_icon", selector: { icon: {} } },
              { name: "speaker_icon", selector: { icon: {} } },
            ],
          },
          { name: "active_color", selector: { ui_color: { default_color: DEFAULT_CONFIG.active_color } } },
          ...cardOnly([{ name: "show_timer", selector: { boolean: {} } }]),
        ],
      },
      {
        name: "recording",
        type: "expandable",
        flatten: true,
        icon: "mdi:microphone-settings",
        schema: [
          {
            name: "",
            type: "grid",
            schema: [
              { name: "max_duration", selector: number(1, 120, 1) },
              { name: "min_duration", selector: number(0, 30, 0.1) },
            ],
          },
          { name: "auto_play", selector: { boolean: {} } },
          { name: "announce", selector: { boolean: {} } },
          { name: "playback_start_delay", selector: number(0, 15, 0.1) },
        ],
      },
      {
        name: "audio",
        type: "expandable",
        flatten: true,
        icon: "mdi:waveform",
        schema: [
          {
            name: "input_profile",
            selector: { select: { mode: "dropdown", options: this._options(Object.keys(INPUT_PROFILES), "input.") } },
          },
          {
            name: "output_profile",
            selector: { select: { mode: "dropdown", options: this._options(OUTPUT_PROFILES, "output.") } },
          },
          {
            name: "transcoding",
            selector: { select: { mode: "dropdown", options: this._options(TRANSCODING_MODES, "transcoding.") } },
          },
          {
            name: "input_mime_candidates",
            selector: { select: { multiple: true, reorder: true, mode: "dropdown", options: INPUT_MIME_OPTIONS } },
          },
          {
            name: "",
            type: "grid",
            schema: Object.keys(TRANSCODE_FIELDS).map(transcodeField),
          },
          { name: "output_passthrough_rules", selector: { object: {} } },
        ],
      },
      {
        name: "styles",
        type: "expandable",
        flatten: true,
        icon: "mdi:code-braces",
        schema: [css("button_css"), ...cardOnly([css("status_css"), css("timer_css"), css("text_css")])],
      },
    ];
  }

  _formData() {
    const config = this._config || {};
    const target = isPlainObject(config.transcode_target) ? config.transcode_target : {};
    const data = { ...DEFAULT_CONFIG, ...config, entity_id: getTargets(config) };
    for (const [name, field] of Object.entries(TRANSCODE_FIELDS)) {
      data[name] = target[field.key] === undefined ? undefined : String(target[field.key]);
    }
    return data;
  }

  _valueChanged(value) {
    const next = { ...this._config };
    const isEmpty = (item) =>
      item === undefined || item === null || item === "" || (Array.isArray(item) && !item.length);

    for (const key of Object.keys(DEFAULT_CONFIG)) {
      const item = value[key];
      if (isEmpty(item) || item === DEFAULT_CONFIG[key]) {
        delete next[key];
      } else {
        next[key] = item;
      }
    }

    const targets = getTargets(value);
    next.entity_id = targets.length === 1 ? targets[0] : targets;

    for (const key of ["input_mime_candidates", "output_passthrough_rules"]) {
      if (isEmpty(value[key])) {
        delete next[key];
      } else {
        next[key] = value[key];
      }
    }

    const transcodeTarget = {};
    for (const [name, field] of Object.entries(TRANSCODE_FIELDS)) {
      if (!isEmpty(value[name])) {
        transcodeTarget[field.key] = ["sample_rate", "channels"].includes(field.key)
          ? Number(value[name])
          : value[name];
      }
    }
    if (Object.keys(transcodeTarget).length) {
      next.transcode_target = transcodeTarget;
    } else {
      delete next.transcode_target;
    }

    if (JSON.stringify(next) === JSON.stringify(this._config)) {
      return;
    }
    this._config = next;
    this._form.schema = this._schema();
    this._form.data = this._formData();
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config: next }, bubbles: true, composed: true })
    );
  }

  _computeLabel(schema) {
    if (schema.type === "expandable") {
      return this._t(`editor.${schema.name}`);
    }
    return this._t(`label.${schema.name}`);
  }

  _computeHelper(schema) {
    const name = schema.name;
    if (name === "input_profile") {
      const mime = pickSupportedMimeType(getInputMimeCandidates(this._config));
      return this._t("helper.input_profile", { mime: mime || this._t("helper.browser_default") });
    }
    if (name === "output_profile") {
      return this._t(`output.${this._config?.output_profile || DEFAULT_CONFIG.output_profile}.desc`);
    }
    if (name === "transcoding") {
      return this._t(`transcoding.${this._config?.transcoding || DEFAULT_CONFIG.transcoding}.desc`);
    }
    if (String(name).startsWith("transcode_")) {
      return this._t("helper.transcode");
    }
    if (String(name).endsWith("_css")) {
      return this._t("helper.css");
    }
    const key = `helper.${name}`;
    const text = this._t(key);
    return text === key ? undefined : text;
  }
}

function defineElements() {
  for (const [tag, element] of [
    [VOICE_ANNOUNCEMENT_TAG, VoiceAnnouncementCard],
    [EDITOR_TAG, VoiceAnnouncementCardEditor],
    [VOICE_ANNOUNCEMENT_BADGE_TAG, VoiceAnnouncementBadge],
  ]) {
    if (!window.customElements.get(tag)) {
      window.customElements.define(tag, element);
    }
  }
}

defineElements();
// The frontend loads this module in parallel with its own bundle, which may then replace
// window.customElements with a scoped-registry polyfill. Define again once the app is up.
window.customElements.whenDefined("home-assistant").then(defineElements);

function registerPickerEntry(collectionName, type, name, description) {
  const collection = (window[collectionName] = window[collectionName] || []);
  const entry = {
    type,
    name,
    description,
    preview: false,
    documentationURL: DOCUMENTATION_URL,
    getEntitySuggestion: (_hass, entityId) =>
      entityId?.startsWith("media_player.")
        ? { config: { type: `custom:${type}`, entity_id: entityId } }
        : null,
  };
  const index = collection.findIndex((item) => item?.type === type);
  if (index >= 0) {
    collection[index] = entry;
  } else {
    collection.push(entry);
  }
}

registerPickerEntry(
  "customCards",
  VOICE_ANNOUNCEMENT_TAG,
  "Voice Announcement",
  "Record a voice message and play it on one or more speakers."
);
registerPickerEntry(
  "customBadges",
  VOICE_ANNOUNCEMENT_BADGE_TAG,
  "Voice Announcement",
  "Record a voice message from a badge and play it on your speakers."
);
