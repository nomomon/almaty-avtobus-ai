export function getApiHeaders(options?: {
  accept?: string;
  contentType?: string;
  referrer?: string;
  extra?: Record<string, string>;
}): Record<string, string> {
  const baseHeaders: Record<string, string> = {
    "x-auth-token":
      "03AFcWeA5kkpiC_2Ih04wu30m4fzy_xA_teFWlUz2VQPy-G1tffoVQaCABBb8vK9cBNMcrrRkIakRXUGfqnxr_D257DKSw0r6XqFYsBSu4o3b0DrpFYoTRRdJ3KQpeMvYfogrkGYfblhFajdR8tZmsPPoNyZwCJWxaR7gHWcMm1h_83AG2XiSHmDye-w4J2NiOJbjfVLBO5Bdz9PjnOsX2HdM0AJbC5osMF_Tiu1gp6yins4Vc2cx5izKcfI4FEBm4xLUXWR8OMtzy-430Jkjjt4vzeQ3YUQFHUEs6X-_o8Xu32qCH_ygUJ5dzekopzGVtRNBzycLTuUJnMjoiU6Hu977xpoZFi8LVlWQcoj0BDPwPv1vP2mfbQYU-zZ-iZy4ZP4RBX6FYPHzardjUR1tOAac3m41YXl_5U1INv_gyMLc4ElUd2xCjByutzFQ-DrvFGWeit7TQJENaTpg9aDZE2WRbNzv7mtHzMuD7I1C6nTBgXIJh5jbBQv1Y7CW_rr_MiHQk--B_yoRgknymMjaIxjd13ySpxgslFWCJ3zZAlTvxfmxOQ89N5RkkWNm5c2YovPUPf7wSMg6hjxwDUOe6cYVakkd3R8iKN5xG2anXgDLxcrT3_9IpC_K3nJq5An249ieUqDcvWOjnNvcMB-WXReJ7hHn-zJmKwt6CNJu0PonaGs7uX17nRVvu2eSvy9pfTla21jKT3Eu0H6dh4dsZ0dZwKHQS8Edequ_2CI4oRCSChkll_u6WAd0moKgF4Ugu5q-z3mot1ohZvU-U_ycfZSEm1-zAq9nodEDcwkHviqrC5_qzKTKAi0AnMD8hOaREVKyzWgiP186lsNKh4L3jlLdj_OlQ15xAKKCcI7sf64gXXP_fIEg1my4bUAYbo4k4U9xI2Vjkcvit7XTEjR3J1gbFN8YDypFC5NrkqwC_NHjnKu-WsTXMlxA",
    "x-visitor-id": "32ab9824c76b4254c6760f8ac7f7f303",
  };
  if (options?.accept) baseHeaders["accept"] = options.accept;
  if (options?.contentType) baseHeaders["content-type"] = options.contentType;
  if (options?.extra) Object.assign(baseHeaders, options.extra);
  return baseHeaders;
}
