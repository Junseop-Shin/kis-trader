package com.kistrader.backend.service;

import com.kistrader.backend.dto.KisDailyPriceResponse;
import com.kistrader.backend.dto.KisTokenRequest;
import com.kistrader.backend.dto.KisTokenResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestParam;

@FeignClient(name = "kisApi", url = "${kis.base-url:https://openapi.koreainvestment.com:9443}")
public interface KisFeignClient {

    @PostMapping("/oauth2/tokenP")
    KisTokenResponse getToken(@RequestBody KisTokenRequest request);

    @GetMapping("/uapi/domestic-stock/v1/quotations/inquire-daily-price")
    KisDailyPriceResponse getDailyPrice(
            @RequestHeader("Authorization") String authorization,
            @RequestHeader("appkey") String appKey,
            @RequestHeader("appsecret") String appSecret,
            @RequestHeader("tr_id") String trId, // FHKST01010100
            @RequestParam("FID_COND_MRKT_DIV_CODE") String marketDivCode, // J
            @RequestParam("FID_INPUT_ISCD") String ticker,
            @RequestParam("FID_INPUT_DATE_1") String startDate,
            @RequestParam("FID_INPUT_DATE_2") String endDate,
            @RequestParam("FID_PERIOD_DIV_CODE") String periodDivCode, // D
            @RequestParam("FID_ORG_ADJ_PRC") String orgAdjPrc // 0
    );

    @GetMapping("/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice")
    String getMinuteChartPrice(
            @RequestHeader("Authorization") String authorization,
            @RequestHeader("appkey") String appKey,
            @RequestHeader("appsecret") String appSecret,
            @RequestHeader("tr_id") String trId, // FHKST03010200
            @RequestParam("FID_ETC_CLS_CODE") String etcClsCode, // ""
            @RequestParam("FID_COND_MRKT_DIV_CODE") String marketDivCode, // J
            @RequestParam("FID_INPUT_ISCD") String ticker,
            @RequestParam("FID_INPUT_HOUR_1") String time, // HHMMSS
            @RequestParam("FID_PW_DATA_INCU_YN") String pwDataIncuYn // N
    );
}
