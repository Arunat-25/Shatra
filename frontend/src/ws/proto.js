const PROTO_V2 = 2;

/** Game client uses WS v2 only (Stage 8). */
export function wsProtoVersion() {
  return PROTO_V2;
}

export { PROTO_V2 };
