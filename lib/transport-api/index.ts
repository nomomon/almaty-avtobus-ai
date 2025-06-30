export function getApiHeaders(options?: {
  accept?: string;
  contentType?: string;
  referrer?: string;
  extra?: Record<string, string>;
}): Record<string, string> {
  const baseHeaders: Record<string, string> = {
    "x-auth-token":
      "03AFcWeA7X7dkTlK0EJCZJkdZLUHTkB-86EdFLUpz51QGRdpeCX1ThFXxyzOWn5jtyw30eKJL9Ea8pcJ7otKs7z-q2jBzvpVFXQhLh9bc6G1Zat4R3wCPcPEBMh8y1pSTRNOE9nfOgCe43Juzh-4SUGLRAXN3O90nOz_s9Vw8xK03IdUyG2XWyEXox8R6AxUsTtMZ3gleIyeVBQrRSJAZ3RpIhazmI1xFupsosiAxb1JKUjUcG6PiYYz2_EMo7dDD9xTyplCYWYhDVSs8HCY8ln5rs4SEmD1rvxM83bhlVYdKDN0aMwn3l4JnTj2SU-XKb3zP1gNSMf60XxexqNaNn7v111z2kHUdrwIe8KJlTmlAS2er6uYInZlmhweDqXo58eOJkQ2Y2YdWWAefnWeKxqBXTWxJ8qOdZVdD0JQWTjTAi6uTbPC9wyyUwrpZii0qDA6nz6vqqmmjoA_fGdIN_UWKf31yZnAG3a_rOtHgbljy-QVeM_D9JIg3Q9gbj8EpUBas0Gq1k8L-9nwc7sUbK_W34muaC813-5Y0T0snIyJT6a4XBWLsxTZN5QIiVyO6kyLxDNHZn_DL60nHw9o7dYm7UBywMwdiH6T_nI_R8fuy8EfYoLnV28AhUTqNYLmUkys0NsFxSK1o7kCZ8h8V0VlEpuSmCYwVAtveDLdEok08JGdkXXCEEorUMAQ-cssQ5tM8KGrS80hCGyN4uZU8g6muGOJSf2siAvD0OzHDNyBvxSDDyn0SgmOm37jqFcVeqxpnNrN_MFp1DJJlSHNLoHWTGhR1pCrI2O9IGQlWIx34GK3UYSQv50VlBzYSkS_GVn6P69rsz7XsSatrj1Kxzmkp_n4vwVbUCtHvI7r9L69zxiht64xCPiByioFCRlNyd7JrXVWvED3POv0x50jOcOVtS2Ixx1MO7yz8spiWWy_K5YFLxXnQAiQc",
    "x-visitor-id": "32ab9824c76b4254c6760f8ac7f7f303",
  };
  if (options?.accept) baseHeaders["accept"] = options.accept;
  if (options?.contentType) baseHeaders["content-type"] = options.contentType;
  if (options?.extra) Object.assign(baseHeaders, options.extra);
  return baseHeaders;
}
