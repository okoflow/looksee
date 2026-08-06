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
}: NegotiateSdpArgs): Promise<void> {
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

  const answerSdp = await response.text();

  await peerConnection.setRemoteDescription({ type: "answer", sdp: answerSdp });
}
