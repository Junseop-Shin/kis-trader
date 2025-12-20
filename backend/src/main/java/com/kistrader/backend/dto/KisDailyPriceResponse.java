package com.kistrader.backend.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import java.util.List;

@Data
public class KisDailyPriceResponse {
    @JsonProperty("msg1")
    private String message;

    @JsonProperty("rt_cd")
    private String returnCode;

    @JsonProperty("output")
    private List<DailyPriceOutput> output;

    @Data
    public static class DailyPriceOutput {
        @JsonProperty("stck_bsop_date")
        private String date; // YYYYMMDD

        @JsonProperty("stck_clpr")
        private String closePrice;

        @JsonProperty("stck_oprc")
        private String openPrice;

        @JsonProperty("stck_hgpr")
        private String highPrice;

        @JsonProperty("stck_lwpr")
        private String lowPrice;

        @JsonProperty("acml_vol")
        private String volume;
    }
}
