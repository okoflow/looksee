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
  const peerConnection = new RTCPeerConnection({ iceServers: [] });

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
    for (const sender of peerConnection.getSenders()) {
      sender.track?.stop();
    }

    peerConnection.close();
  };

  signal.addEventListener("abort", close, { once: true });

  try {
    await negotiateSdp({
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
