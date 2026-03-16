package com.kistrader.backend.service;

import lombok.RequiredArgsConstructor;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class NotificationService {

    private final SimpMessagingTemplate messagingTemplate;

    public void sendTradeNotification(Long userId, Object payload) {
        messagingTemplate.convertAndSendToUser(
                String.valueOf(userId),
                "/queue/trades",
                payload
        );
    }

    public void broadcastMarketUpdate(Object payload) {
        messagingTemplate.convertAndSend("/topic/market", payload);
    }

    public void sendBacktestResult(Long userId, Object payload) {
        messagingTemplate.convertAndSendToUser(
                String.valueOf(userId),
                "/queue/backtest",
                payload
        );
    }
}
