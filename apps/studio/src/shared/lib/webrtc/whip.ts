import { negotiateSdp } from "./sdp";

export interface WhipHandle {
  close: () => void;
  peerConnection: RTCPeerConnection;
}

const H264_INTEROP_MIME_TYPES = ["video/H264", "video/rtx", "video/red", "video/ulpfec"];

function preferH264(transceiver: RTCRtpTransceiver) {
  const codecs = RTCRtpSender.getCapabilities("video")?.codecs ?? [];

  const preferred = codecs.filter((codec) => {
    return H264_INTEROP_MIME_TYPES.includes(codec.mimeType);
  });

  if (preferred.some((codec) => codec.mimeType === "video/H264")) {
    transceiver.setCodecPreferences(preferred);
  }
}

function whipResponseError(response: Response): Error {
  return new Error(`WHIP ${response.status} ${response.statusText}`);
}

export async function publishWhip(
  whipUrl: string,
  authorization: string,
  stream: MediaStream,
  signal: AbortSignal
): Promise<WhipHandle> {
  signal.throwIfAborted();

  const peerConnection = new RTCPeerConnection({ iceServers: [] });
  let closeSession: (() => void) | undefined;

  for (const track of stream.getTracks()) {
    const transceiver = peerConnection.addTransceiver(track, {
      direction: "sendonly",
      streams: [stream],
    });

    if (track.kind === "video") {
      preferH264(transceiver);
    }
  }

  const close = () => {
    signal.removeEventListener("abort", close);
    peerConnection.close();
    closeSession?.();
  };

  signal.addEventListener("abort", close, { once: true });

  try {
    closeSession = await negotiateSdp({
      authorization,
      mapErrorResponse: whipResponseError,
      peerConnection,
      signal,
      url: whipUrl,
    });
  } catch (caught) {
    close();

    throw caught;
  }

  return { peerConnection, close };
}
