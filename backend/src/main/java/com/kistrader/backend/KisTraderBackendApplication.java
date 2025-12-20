package com.kistrader.backend;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@EnableFeignClients
public class KisTraderBackendApplication {

    public static void main(String[] args) {
        SpringApplication.run(KisTraderBackendApplication.class, args);
    }

}
