package com.kistrader.backend.batch;

import com.kistrader.backend.domain.stock.Stock;
import com.kistrader.backend.repository.DailyPriceRepository;
import com.kistrader.backend.repository.StockRepository;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobExecution;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import com.kistrader.backend.dto.KisDailyPriceResponse;
import com.kistrader.backend.dto.KisTokenResponse;
import com.kistrader.backend.service.KisFeignClient;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Date;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;

@SpringBootTest
@ActiveProfiles("test")
public class StockPriceJobIntegrationTest {

    @Autowired
    private JobLauncher jobLauncher;

    @Autowired
    private Job jobSyncStockPrices;

    @Autowired
    private StockRepository stockRepository;

    @Autowired
    private DailyPriceRepository dailyPriceRepository;

    @MockitoBean
    private KisFeignClient kisFeignClient;

    @Test
    public void testJobRun_UpsertDailyPrices() throws Exception {
        // Given
        Stock samsung = Stock.builder()
                .ticker("005930")
                .name("Samsung Electronics")
                .marketType("KOSPI")
                .build();
        stockRepository.save(samsung);

        // Mock Token Response
        KisTokenResponse tokenResponse = new KisTokenResponse();
        tokenResponse.setAccessToken("mock_token");
        tokenResponse.setExpiresIn(3600);
        given(kisFeignClient.getToken(any())).willReturn(tokenResponse);

        // Mock Price Response
        KisDailyPriceResponse priceResponse = new KisDailyPriceResponse();
        KisDailyPriceResponse.DailyPriceOutput output = new KisDailyPriceResponse.DailyPriceOutput();
        output.setDate(LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE)); // Today
        output.setClosePrice("70000");
        output.setOpenPrice("69500");
        output.setHighPrice("70500");
        output.setLowPrice("69000");
        output.setVolume("1000000");
        priceResponse.setOutput(List.of(output));

        given(kisFeignClient.getDailyPrice(any(), any(), any(), any(), any(), any(), any(), any(), any(), any()))
                .willReturn(priceResponse);

        // When
        JobParameters jobParameters = new JobParametersBuilder()
                .addDate("timestamp", new Date())
                .toJobParameters();

        JobExecution jobExecution = jobLauncher.run(jobSyncStockPrices, jobParameters);

        // Then
        Assertions.assertEquals("COMPLETED", jobExecution.getExitStatus().getExitCode());

        long count = dailyPriceRepository.count();
        Assertions.assertTrue(count > 0, "Should have inserted at least 1 daily price record");

        dailyPriceRepository.findAll().forEach(price -> {
            System.out.println("Saved Price: " + price.getTicker() + " / " + price.getClose());
            Assertions.assertEquals("005930", price.getTicker());
        });
    }
}
