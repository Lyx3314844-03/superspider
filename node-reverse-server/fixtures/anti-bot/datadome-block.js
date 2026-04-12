window.ddResObj = { cid: "abc", hsh: "def" };
const challenge = {
  canvas: document.createElement("canvas").toDataURL(),
  audio: new AudioContext(),
  fingerprint: navigator.userAgent + screen.width
};
