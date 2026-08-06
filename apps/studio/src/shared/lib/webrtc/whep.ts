import { negotiateSdp } from "./sdp";

export class WhepNoStreamError extends Error {
  constructor() {
    super("No active stream — the camera is not publishing yet");

    this.name = "WhepNoStreamError";
  }
}

function whepResponseError(response: Response): Error {
  if (response.status === 404) {
    return new WhepNoStreamError();
  }

  return new Error(`WHEP ${response.status} ${response.statusText}`);
}

export async function playWhep(
  whepUrl: string,
  authorization: string,
  video: HTMLVideoElement,
  signal: AbortSignal
): Promise<RTCPeerConnection> {
  const peerConnection = new RTCPeerConnection({ iceServers: [] });

  peerConnection.addTransceiver("video", { direction: "recvonly" });
  peerConnection.addTransceiver("audio", { direction: "recvonly" });

  peerConnection.ontrack = (event) => {
    const [stream] = event.streams;

    if (stream) {
      video.srcObject = stream;
    }
  };

  const close = () => {
    peerConnection.close();

    video.srcObject = null;
  };

  signal.addEventListener("abort", close, { once: true });

  try {
    await negotiateSdp({
      authorization,
      mapErrorResponse: whepResponseError,
      peerConnection,
      signal,
      url: whepUrl,
    });
  } catch (caught) {
    close();

    throw caught;
  }

  return peerConnection;
}
