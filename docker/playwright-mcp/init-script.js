Object.defineProperty(navigator, "webdriver", {
  get: () => undefined,
});

Object.defineProperty(navigator, "languages", {
  get: () => ["en-US", "en"],
});

Object.defineProperty(navigator, "platform", {
  get: () => "Linux x86_64",
});

Object.defineProperty(navigator, "hardwareConcurrency", {
  get: () => 8,
});

Object.defineProperty(navigator, "deviceMemory", {
  get: () => 8,
});

Object.defineProperty(navigator, "maxTouchPoints", {
  get: () => 0,
});

Object.defineProperty(navigator, "plugins", {
  get: () => {
    const plugins = [
      { name: "Chrome PDF Plugin", filename: "internal-pdf-viewer", description: "Portable Document Format" },
      { name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai", description: "" },
      { name: "Native Client", filename: "internal-nacl-plugin", description: "" },
    ];
    plugins.refresh = () => {};
    return plugins;
  },
});

Object.defineProperty(navigator, "mimeTypes", {
  get: () => {
    const mimeTypes = [
      { type: "application/pdf", suffixes: "pdf", description: "Portable Document Format" },
      { type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format" },
      { type: "application/x-nacl", suffixes: "", description: "Native Client Executable" },
    ];
    return mimeTypes;
  },
});

if (window.chrome === undefined) {
  window.chrome = {};
}
window.chrome.runtime = {
  connect: () => {},
  sendMessage: () => {},
};

const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => {
  if (parameters.name === "notifications") {
    return Promise.resolve({ state: Notification.permission });
  }
  return originalQuery(parameters);
};

const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function (parameter) {
  if (parameter === 37445) {
    return "Google Inc. (Intel)";
  }
  if (parameter === 37446) {
    return "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630, OpenGL 4.6)";
  }
  return getParameter.call(this, parameter);
};

const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
WebGL2RenderingContext.prototype.getParameter = function (parameter) {
  if (parameter === 37445) {
    return "Google Inc. (Intel)";
  }
  if (parameter === 37446) {
    return "ANGLE (Intel, Mesa Intel(R) UHD Graphics 630, OpenGL 4.6)";
  }
  return getParameter2.call(this, parameter);
};

const originalGetContext = HTMLCanvasElement.prototype.getContext;
HTMLCanvasElement.prototype.getContext = function (type, attributes) {
  if (type === "webgl" || type === "webgl2") {
    attributes = Object.assign({}, attributes, {
      preserveDrawingBuffer: true,
    });
  }
  return originalGetContext.call(this, type, attributes);
};

Object.defineProperty(document, "hidden", {
  get: () => false,
});

Object.defineProperty(document, "visibilityState", {
  get: () => "visible",
});

window.outerWidth = window.innerWidth;
window.outerHeight = window.innerHeight + 85;
