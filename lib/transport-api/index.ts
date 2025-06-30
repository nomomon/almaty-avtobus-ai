export function getApiHeaders(options?: {
  accept?: string;
  contentType?: string;
  referrer?: string;
  extra?: Record<string, string>;
}): Record<string, string> {
  const baseHeaders: Record<string, string> = {
    "x-auth-token":
      "03AFcWeA5KoJSPIlD2J-ADa7f0wud1EG6v_LdvFT9IfgJWjR7cY-4BDMpHFGPOGA6mFISCVVB4owIMEQ31gZ4sRfLvPrNugdwb0a_3FPRJ9W3ZdhM7An_1q2fyKqPiVSkJzhkhf2zd8viHLrAk7MsHhuHX_SjlnOXmvHHZrjWKJRAjmEIBl6ovAG_0PJZ8PYInqDzdhmOymYTS0CZ-ukzIoswvtE3UFjW137Rzb-zJme-zjC_A-z5htOanPAS6l5T2qcCS-pzmJ8Mg6jPgsV_LmTlujonhS82WYtlncnrAeKRJfueRp5Au4JoHyML7CWu7ImRxwjWI0EJC9tKoubjbh2styjhJqBbj_-yI_ORux1nuQx40pjHe-RivaQkCW9uEKyUamoA3jEiGauk6gVpV3SIkytEZnEJ3SvXZclr0IdfcRqyCMIinkNaHnaB3czQOjhIr2h0B44PYdzDnpoKROU061GJP0Bm733twOieUhQkFkKjsAk_CTM8KO4VkHmaTaz1b6_ugQj94Ippm8y3F8TA2tmXw58rllLsrdjYBnANUnbMoAYGrR2fxxU6pN_9-GUyXqe1JI8SlWsNLYWhA-k4aXPkMxpSzF_iSba9f5UdMPyzwbmZJ6HgSkWi11GljdzwGMmyDv_OpXU6wk_ooiwcv8RCuV8w6HOOejFBIpoW7WNqRs50St79cdgtuPx92gsTJIFvzJbrx0Q4XL8Xu5LjAcqBi0GrXs2X6m_QaznqtMBwWhQe3x40788RYvyv8X2g1BXRp_XJuQ2eUphtDvrV0epcLlgq_HW_VQD4AIz2etZ339Qu1JYIDxgb-I56e93sHClJYwNNLhyfSDdnh7T4_2Aa88_U7HKHZR7rosUeIComcLqhm4Ady6NYdFJJxZePDvSnpVvVz_a9p1O9rkG2Kkocs1jvj_8ULtbTfThO_62ellEU9Wd4",
    "x-visitor-id": "32ab9824c76b4254c6760f8ac7f7f303",
  };
  if (options?.accept) baseHeaders["accept"] = options.accept;
  if (options?.contentType) baseHeaders["content-type"] = options.contentType;
  if (options?.extra) Object.assign(baseHeaders, options.extra);
  return baseHeaders;
}
