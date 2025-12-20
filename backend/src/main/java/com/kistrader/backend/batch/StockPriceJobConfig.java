package com.kistrader.backend.batch;

import com.kistrader.backend.domain.price.DailyPrice;
import com.kistrader.backend.domain.stock.Stock;
import com.kistrader.backend.repository.DailyPriceRepository;
import com.kistrader.backend.service.KisApiService;
import jakarta.persistence.EntityManagerFactory;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.launch.support.RunIdIncrementer;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.ItemWriter;
import org.springframework.batch.item.database.JpaPagingItemReader;
import org.springframework.batch.item.database.builder.JpaPagingItemReaderBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

@Slf4j
@Configuration
@RequiredArgsConstructor
public class StockPriceJobConfig {

    private final EntityManagerFactory entityManagerFactory;
    private final JobRepository jobRepository;
    private final PlatformTransactionManager transactionManager;
    private final DailyPriceRepository dailyPriceRepository;

    private final KisApiService kisApiService;
    private static final int CHUNK_SIZE = 10;

    @Bean
    public Job jobSyncStockPrices() {
        return new JobBuilder("jobSyncStockPrices", jobRepository)
                .incrementer(new RunIdIncrementer())
                .start(stepSyncDailyPrices())
                .build();
    }

    @Bean
    public Step stepSyncDailyPrices() {
        return new StepBuilder("stepSyncDailyPrices", jobRepository)
                .<Stock, DailyPrice>chunk(CHUNK_SIZE, transactionManager)
                .reader(stockReader())
                .processor(stockPriceProcessor())
                .writer(dailyPriceWriter())
                .build();
    }

    @Bean
    public JpaPagingItemReader<Stock> stockReader() {
        return new JpaPagingItemReaderBuilder<Stock>()
                .name("stockReader")
                .entityManagerFactory(entityManagerFactory)
                .pageSize(CHUNK_SIZE)
                .queryString("SELECT s FROM Stock s")
                .build();
    }

    @Bean
    public ItemProcessor<Stock, DailyPrice> stockPriceProcessor() {
        return stock -> {
            log.info("Processing stock for sync: {}", stock.getTicker());
            // Fetch current price (or daily history)
            return kisApiService.fetchCurrentPrice(stock.getTicker());
        };
    }

    @Bean
    public ItemWriter<DailyPrice> dailyPriceWriter() {
        return items -> {
            log.info("Saving {} daily prices...", items.size());
            dailyPriceRepository.saveAll(items);
        };
    }
}
