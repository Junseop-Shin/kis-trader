package com.kistrader.backend.service;

import com.kistrader.backend.domain.price.DailyPrice;
import com.kistrader.backend.dto.KisDailyPriceResponse;
import com.kistrader.backend.dto.KisTokenRequest;
import com.kistrader.backend.dto.KisTokenResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;

@Slf4j
@Service
@RequiredArgsConstructor
public class KisApiService {

    private final KisFeignClient kisFeignClient;

    @Value("${kis.appkey}")
    private String appKey;

    @Value("${kis.appsecret}")
    private String appSecret;

    private String accessToken;
    private long tokenExpirationTime = 0;

    /**
     * Retrieves a valid access token. Simplistic in-memory caching.
     */
    private String getAccessToken() {
        if (accessToken != null && System.currentTimeMillis() < tokenExpirationTime) {
            return accessToken;
        }

        log.info("KIS API: Requesting new Access Token...");
        KisTokenRequest request = KisTokenRequest.builder()
                .grantType("client_credentials")
                .appKey(appKey)
                .appSecret(appSecret)
                .build();

        KisTokenResponse response = kisFeignClient.getToken(request);
        this.accessToken = response.getAccessToken();
        // Set expiry locally (buffer 60sec)
        this.tokenExpirationTime = System.currentTimeMillis() + (response.getExpiresIn() * 1000L) - 60000;

        log.info("KIS API: Access Token acquired. Expires in {} sec", response.getExpiresIn());
        return this.accessToken;
    }

    public DailyPrice fetchCurrentPrice(String ticker) {
        String token = "Bearer " + getAccessToken();
        String today = LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE);

        log.info("KIS API: Fetch Current Price for {} (Date: {})", ticker, today);

        try {
            // KIS API constraints:
            // FID_COND_MRKT_DIV_CODE: J (Stock)
            // FID_PERIOD_DIV_CODE: D (Daily)
            KisDailyPriceResponse response = kisFeignClient.getDailyPrice(
                    token,
                    appKey,
                    appSecret,
                    "FHKST01010100", // Transaction ID for Daily Price
                    "J",
                    ticker,
                    today,
                    today,
                    "D",
                    "0");

            if (response == null || response.getOutput() == null || response.getOutput().isEmpty()) {
                log.warn("KIS API: No data found for ticker {}", ticker);
                return null;
            }

            KisDailyPriceResponse.DailyPriceOutput output = response.getOutput().get(0);

            return DailyPrice.builder()
                    .ticker(ticker)
                    .date(LocalDate.parse(output.getDate(), DateTimeFormatter.BASIC_ISO_DATE))
                    .close(new BigDecimal(output.getClosePrice()))
                    .open(new BigDecimal(output.getOpenPrice()))
                    .high(new BigDecimal(output.getHighPrice()))
                    .low(new BigDecimal(output.getLowPrice()))
                    .volume(Long.parseLong(output.getVolume()))
                    .build();

        } catch (Exception e) {
            log.error("KIS API Error for ticker {}: {}", ticker, e.getMessage());
            return null; // Skip this item in Batch
        }
    }
}
