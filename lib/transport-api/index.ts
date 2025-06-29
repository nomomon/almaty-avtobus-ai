export function getApiHeaders(options?: {
  accept?: string;
  contentType?: string;
  referrer?: string;
  extra?: Record<string, string>;
}): Record<string, string> {
  const baseHeaders: Record<string, string> = {
    "x-auth-token":
      "03AFcWeA78I8tKQr46JT7x1br9yuJtInqvxRuedBCRup5Q5f6B9NAQHH_ozf7HiuRKmrCVqIaRAm_abfvjxF2frEU0anu23ddynU2B2YZaWrhZmqgO2QfHjveFMDKqwu8AZcIoBkYqDMB-IfksOeou3sTRsV-sihmavzIJpFalScRU-narrYVy5UDD2Ok_jltOMu5-nLA0w4rImCD1NBLkzjn-SwfM7SBegcgmbYURIpjZr0JOQgpj9nya7Y99GDPHrioOwXNGmn_Z-4Mre8QpMl5KNMjipmwUVk__zGXckqBUBFXhaXGuvXTtJRDoBtORKWNExk7MURJj7rguKK8BNJI0ZDoh4WuZVCcPzpTmxOui0GtBFFzFDGAHMEiAxwRn8UJLy4PPJp1wDejlHN-b_kGLBsEV77JaUpoQQeijFe7Ffvz2WT_xZIr5oaXwn-MX660Nm2-pUihGTyha_Wn4RUPx8lVq4VuLRDINzAUFeJC7-pMa9yaINS-HaJ27FbtVRrUcfJ9bpIHTOAqYOzdSgFFzQucNQk6conIAVTaxO9mU6euTEeUC8euEWc108rAbMv4j9F5pWh_lSp5_kLojCLsJOGF-j77hTnOmXV7V-zA5XwJzi5qreqWnuvfdpJnadkF66lt9NpM4OlYjHRw6z5lxVGUzYG99fAo4BTiGmc9FG2c5F0zgXruCHroRd75NpOofagsG_UIKJ1qw4i55piGk6iDEEp9usBLwCsVFj7Nrg0Btme5Y_ogLK-fPDeU71xn4D-DYrWeLasWoDvHowObQo6F4-d4iOk3Wvqe0ozRJigS1kCWLgioQJTxNToLt74dfkaE4WzLNl8_t4-FlOza5EV0spOC5hvsdCk4qCDrk4w8W_SczzcBYHOQ-8XpTtX2IVxzKlqKTFCzLsVW11oRQhr9aYbZeVIq80ZXh8U6cusv6XRG78N4",
    "x-visitor-id": "32ab9824c76b4254c6760f8ac7f7f303",
  };
  if (options?.accept) baseHeaders["accept"] = options.accept;
  if (options?.contentType) baseHeaders["content-type"] = options.contentType;
  if (options?.extra) Object.assign(baseHeaders, options.extra);
  return baseHeaders;
}
