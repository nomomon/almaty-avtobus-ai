export function getApiHeaders(options?: {
  accept?: string;
  contentType?: string;
  referrer?: string;
  extra?: Record<string, string>;
}): Record<string, string> {
  const baseHeaders: Record<string, string> = {
    "x-auth-token":
      "03AFcWeA7ZuKcWf98BZDjTOzV9O-O8Va1XtnsgQJDRWNYkMPRWie-WInjLK9AH36omRxR_dVFQNwj53vqjVViCJlG9tiRKNQGDVKqgM1EH5B1J1HcmFA8dKXnGrUjW2-F_RMRzVonB-cuVL9J5tyA8juvSzFnVKyW1p4gFngT2HHahEPEjSqViLh6evDh6yRTVmgne_VSRXZNeZHsgzOpsu1-Ex_7rO4FcbM9_z_JAf8j75pxjv3P5mC8XAw_wr4n1771A8j6VHcChhCWVdS70RsxMnh-VgjkHE_Bxw590eAqlxTy7eG8yzwo_-okSPYriJaOe7WzhLEnG6jtd8XbVIUAbPw7-DMPubq830S4pATqDcR-uSlP5LYmZ9Jczk6pnCV0PWnqTyWgVtEjLcRO30QjExeveZZiyE226jwFTCi8hzn3QyJiV_qGv_2tmscQdInqH528OdfpMVeIn8XrdkmUgkma1JBxlR2UC7Va8du3FLOoR82OiW_DZ3qASYFPBYx9RCN0ohDHT08IOg21YJfeqvVVtOOvpj1l4KGs9cUUMZNf3ItFGFwbPGYssFTfo_e306tOX1mfCgbvC46T4rydXfGY-iTEDpjp0Jiowe0uwIR0znTmheqYFTXh9JIVY3axfw1dz4ZIwGTRSYZms_sKxuB0yvbYWODv5to_L-RAgEHnm-GNQRI4qmkI-0p11Nde7CAvANr2B1_rQ6GpsAVpY6qjaaiNuOZhW8tCLp-T8chA4vnaPO4XLMpwNi9Zx1pNI0Y0fldNOwK5W8FgHjE9PNarxYYdau0ASxmkiQCFd_n_piVlq9RDgWM2gnGPJNJJtvVHixXa3AEp_ZIm5YDbtuLWSNW200NRVQj6YR3S8yPug7S9fC_8QpqVHzW0keo44t-Ykki6RvfUcfVg41dulTYGnG_tjtfvWgWWhNty1Y-5qCcFIKHs",
    "x-visitor-id": "32ab9824c76b4254c6760f8ac7f7f303",
  };
  if (options?.accept) baseHeaders["accept"] = options.accept;
  if (options?.contentType) baseHeaders["content-type"] = options.contentType;
  if (options?.extra) Object.assign(baseHeaders, options.extra);
  return baseHeaders;
}
