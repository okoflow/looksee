interface NegotiateSdpArgs {
  authorization: string;
  mapErrorResponse: (response: Response) => Error;
  peerConnection: RTCPeerConnection;
  signal: AbortSignal;
  url: string;
}

export async function negotiateSdp({
  authorization,
  mapErrorResponse,
  peerConnection,
  signal,
  url,
}: NegotiateSdpArgs): Promise<(() => void) | undefined> {
  const offer = await peerConnection.createOffer();

  await peerConnection.setLocalDescription(offer);

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/sdp", Authorization: authorization },
    body: offer.sdp,
    signal,
  });

  if (!response.ok) {
    throw mapErrorResponse(response);
  }

  const closeSession = sessionCleanup(response, url, authorization, signal);

  try {
    signal.throwIfAborted();

    const answerSdp = await response.text();

    await peerConnection.setRemoteDescription({ type: "answer", sdp: answerSdp });

    return closeSession;
  } catch (caught) {
    closeSession?.();

    throw caught;
  }
}

function sessionCleanup(response: Response, requestUrl: string, authorization: string, signal: AbortSignal) {
  const location = response.headers.get("Location");

  if (location === null) {
    return;
  }

  const sessionUrl = new URL(location, requestUrl);

  if (sessionUrl.origin !== new URL(requestUrl).origin) {
    throw new Error("Unexpected media session origin");
  }

  let closed = false;
  const close = () => {
    if (closed) {
      return;
    }

    closed = true;
    signal.removeEventListener("abort", close);

    fetch(sessionUrl, {
      method: "DELETE",
      headers: { Authorization: authorization },
      signal: AbortSignal.timeout(5000),
      keepalive: true,
    }).catch(() => undefined);
  };

  signal.addEventListener("abort", close, { once: true });

  return close;
}
