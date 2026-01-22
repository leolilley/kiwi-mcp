# Phase 25: Mobile & Remote Access

**Duration:** 3 weeks  
**Status:** Vision  
**Last Updated:** 2026-01-22  

---

## Overview

Phase 25 extends Mission Control to mobile devices and remote access scenarios, enabling engineers to monitor and manage agent systems from anywhere via iOS/Android apps, progressive web app, and CLI tools.

**Core Focus:**
- iOS & Android native apps
- Progressive Web App (PWA)
- CLI tools (mission-ctl)
- Real-time push notifications
- Offline-first capabilities
- Mobile-optimized UI

---

## Architecture: Multi-Platform

```
┌────────────────────────────────────────────────────┐
│         Mission Control Backend (Unified)          │
├────────────────────────────────────────────────────┤
│  WebSocket | REST API | gRPC                       │
└────────────────────────────────────────────────────┘
    ↙        ↓         ↘        ↖
   iOS     Android    PWA      CLI
┌─────┐  ┌─────────┐ ┌────┐  ┌────────┐
│App  │  │App      │ │Web │  │mission │
│     │  │         │ │App │  │ctl CLI │
└─────┘  └─────────┘ └────┘  └────────┘
```

---

## Week 25.1: iOS App (Swift)

### App Structure

```swift
// MissionControl/App.swift

import SwiftUI

@main
struct MissionControlApp: App {
    @StateObject var authManager = AuthManager()
    @StateObject var mcpClient = MCPWebSocketClient()
    
    var body: some Scene {
        WindowGroup {
            if authManager.isAuthenticated {
                MainTabView()
                    .environmentObject(authManager)
                    .environmentObject(mcpClient)
                    .onAppear {
                        mcpClient.connect(token: authManager.token)
                    }
            } else {
                LoginView()
                    .environmentObject(authManager)
            }
        }
    }
}

// App Tabs
struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "chart.bar.fill")
                }
            
            ThreadsView()
                .tabItem {
                    Label("Threads", systemImage: "list.bullet")
                }
            
            AlertsView()
                .tabItem {
                    Label("Alerts", systemImage: "bell.badge.fill")
                }
            
            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
        }
    }
}
```

### Dashboard for Mobile

```swift
// Views/DashboardView.swift

import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var mcpClient: MCPWebSocketClient
    @State var threads: [Thread] = []
    @State var activeThreadCount = 0
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    // Active Threads Summary
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Active Threads")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text("\(activeThreadCount)")
                                .font(.title2)
                                .fontWeight(.bold)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        
                        VStack(alignment: .leading, spacing: 4) {
                            Text("API Health")
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Label("Good", systemImage: "checkmark.circle.fill")
                                .foregroundColor(.green)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(8)
                    
                    // Recent Alerts
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Recent Alerts")
                            .font(.headline)
                        
                        if let alerts = mcpClient.recentAlerts {
                            ForEach(alerts.prefix(3), id: \.id) { alert in
                                AlertRow(alert: alert)
                            }
                        } else {
                            Text("No recent alerts")
                                .foregroundColor(.secondary)
                                .font(.caption)
                        }
                    }
                    .padding()
                    .background(Color(.systemGray6))
                    .cornerRadius(8)
                    
                    // Thread List
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Active Threads")
                            .font(.headline)
                        
                        ForEach(threads, id: \.id) { thread in
                            NavigationLink(destination: ThreadDetailView(thread: thread)) {
                                ThreadRow(thread: thread)
                            }
                        }
                    }
                    
                    Spacer()
                }
                .padding()
            }
            .navigationTitle("Mission Control")
            .onAppear {
                Task {
                    await loadDashboard()
                }
            }
        }
    }
    
    private func loadDashboard() async {
        threads = await mcpClient.fetchThreads()
        activeThreadCount = threads.filter { $0.status == "running" }.count
    }
}

struct ThreadRow: View {
    let thread: Thread
    
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(thread.userInput.prefix(50))
                    .font(.subheadline)
                    .fontWeight(.semibold)
                Spacer()
                StatusBadge(status: thread.status)
            }
            
            HStack(spacing: 12) {
                Text("Duration: \(thread.durationMs / 1000)s")
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text(thread.mpcId)
                    .font(.caption)
                    .padding(4)
                    .background(Color.blue.opacity(0.2))
                    .cornerRadius(4)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }
}

struct StatusBadge: View {
    let status: String
    
    var body: some View {
        Text(status.uppercased())
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(statusColor)
            .foregroundColor(.white)
            .cornerRadius(4)
    }
    
    var statusColor: Color {
        switch status {
        case "running": return .blue
        case "complete": return .green
        case "error": return .red
        default: return .gray
        }
    }
}
```

### Push Notifications

```swift
// Services/NotificationManager.swift

import UserNotifications

class NotificationManager {
    static let shared = NotificationManager()
    
    func requestAuthorization() async -> Bool {
        do {
            return try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }
    
    func handleNotification(event: MCPEvent) {
        let content = UNMutableNotificationContent()
        
        switch event.type {
        case .alert:
            content.title = "⚠️ Alert"
            content.body = event.data["message"] as? String ?? "New alert"
            content.sound = .default
            
        case .anomaly:
            content.title = "🔍 Anomaly Detected"
            content.body = event.data["description"] as? String ?? "Anomaly detected"
            
        case .sla_breach:
            content.title = "🚨 SLA Breach"
            content.body = event.data["sla_name"] as? String ?? "SLA breached"
            content.sound = UNNotificationSound.default
            
        default:
            return
        }
        
        content.userInfo = [
            "threadId": event.data["thread_id"] ?? "",
            "eventId": event.id,
        ]
        
        let request = UNNotificationRequest(
            identifier: event.id,
            content: content,
            trigger: UNTimeIntervalNotificationTrigger(timeInterval: 1, repeats: false)
        )
        
        UNUserNotificationCenter.current().add(request)
    }
}
```

---

## Week 25.2: Android App (Kotlin)

### App Structure

```kotlin
// com/missioncontrol/MissionControlApp.kt

import androidx.compose.material.Scaffold
import androidx.compose.material.BottomNavigation
import androidx.compose.material.BottomNavigationItem
import androidx.compose.material.Icon
import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

@Composable
fun MissionControlApp(
    authManager: AuthManager,
    mcpClient: MCPWebSocketClient
) {
    val navController = rememberNavController()
    
    Scaffold(
        bottomBar = {
            BottomNavigation {
                BottomNavigationItem(
                    icon = { Icon(Icons.Default.Home, null) },
                    label = { Text("Dashboard") },
                    selected = navController.currentDestination?.route == "dashboard",
                    onClick = { navController.navigate("dashboard") }
                )
                BottomNavigationItem(
                    icon = { Icon(Icons.Default.List, null) },
                    label = { Text("Threads") },
                    selected = navController.currentDestination?.route == "threads",
                    onClick = { navController.navigate("threads") }
                )
                BottomNavigationItem(
                    icon = { Icon(Icons.Default.Notifications, null) },
                    label = { Text("Alerts") },
                    selected = navController.currentDestination?.route == "alerts",
                    onClick = { navController.navigate("alerts") }
                )
                BottomNavigationItem(
                    icon = { Icon(Icons.Default.Settings, null) },
                    label = { Text("Settings") },
                    selected = navController.currentDestination?.route == "settings",
                    onClick = { navController.navigate("settings") }
                )
            }
        }
    ) {
        NavHost(navController, startDestination = "dashboard") {
            composable("dashboard") { DashboardScreen() }
            composable("threads") { ThreadsScreen() }
            composable("alerts") { AlertsScreen() }
            composable("settings") { SettingsScreen() }
        }
    }
}
```

### Push Notifications (FCM)

```kotlin
// com/missioncontrol/services/NotificationService.kt

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MissionControlMessagingService : FirebaseMessagingService() {
    
    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        val eventType = remoteMessage.data["event_type"] ?: return
        
        when (eventType) {
            "alert" -> showAlertNotification(remoteMessage)
            "anomaly" -> showAnomalyNotification(remoteMessage)
            "sla_breach" -> showSLABreachNotification(remoteMessage)
            else -> {}
        }
    }
    
    private fun showAlertNotification(message: RemoteMessage) {
        val notification = NotificationCompat.Builder(this, "alerts")
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle("⚠️ Alert")
            .setContentText(message.data["message"])
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()
        
        NotificationManagerCompat.from(this).notify(
            System.currentTimeMillis().toInt(),
            notification
        )
    }
}
```

---

## Week 25.3: CLI Tool & PWA

### CLI Tool

```bash
#!/usr/bin/env python
# mission-ctl

import click
import json
from mission_control.client import MCPClient

@click.group()
@click.option('--api-key', envvar='MC_API_KEY', required=True)
@click.pass_context
def cli(ctx, api_key):
    """Mission Control CLI"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = MCPClient(api_key=api_key)

@cli.group()
def threads():
    """Manage threads"""
    pass

@threads.command()
@click.pass_context
def list(ctx):
    """List active threads"""
    client = ctx.obj['client']
    threads = client.get_threads()
    
    click.echo(f"Active threads: {len(threads)}\n")
    
    for thread in threads:
        click.echo(f"  {thread['id'][:12]}... | {thread['status']:10} | {thread['user_input'][:40]}")

@threads.command()
@click.argument('thread_id')
@click.pass_context
def inspect(ctx, thread_id):
    """Inspect thread details"""
    client = ctx.obj['client']
    thread = client.get_thread(thread_id)
    
    click.echo(f"Thread: {thread['id']}")
    click.echo(f"Status: {thread['status']}")
    click.echo(f"Duration: {thread['duration_ms']}ms")
    click.echo(f"\nExecution Timeline:")
    
    for step in thread['timeline']:
        click.echo(f"  [{step['duration_ms']:6.1f}ms] {step['description']}")

@cli.group()
def logs():
    """Manage logs"""
    pass

@logs.command()
@click.option('--thread', '-t', help='Filter by thread')
@click.option('--level', '-l', default='INFO', help='Log level')
@click.option('--tail', '-n', default=20, help='Number of lines')
@click.pass_context
def tail(ctx, thread, level, tail):
    """Tail logs in real-time"""
    client = ctx.obj['client']
    
    for log in client.stream_logs(thread=thread, level=level):
        click.echo(f"[{log['timestamp']}] {log['message']}")

@cli.group()
def alerts():
    """Manage alerts"""
    pass

@alerts.command()
@click.pass_context
def list(ctx):
    """List recent alerts"""
    client = ctx.obj['client']
    alerts = client.get_alerts(limit=10)
    
    for alert in alerts:
        icon = "🚨" if alert['severity'] == 'critical' else "⚠️"
        click.echo(f"{icon} {alert['title']} ({alert['severity']})")

if __name__ == '__main__':
    cli()
```

### Progressive Web App

```typescript
// src/app/pwa.tsx

import { useEffect } from 'react'

export function PWASupport() {
  useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('Service worker registered'))
        .catch(err => console.log('Service worker registration failed'))
    }
  }, [])
  
  return null
}

// public/sw.js
const CACHE_NAME = 'mission-control-v1'
const urlsToCache = [
  '/',
  '/index.html',
  '/styles/main.css',
  '/scripts/main.js',
]

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  )
})

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return
  
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
      .catch(() => caches.match('/offline.html'))
  )
})
```

---

## Offline-First Capabilities

### Data Synchronization

```typescript
// services/offlineSync.ts

class OfflineSync {
  private db: IDBDatabase
  
  async initialize() {
    this.db = await this.openDB()
    this.setupSync()
  }
  
  async cacheData(key: string, data: any) {
    const tx = this.db.transaction('cache', 'readwrite')
    tx.objectStore('cache').put({ key, data, timestamp: Date.now() })
  }
  
  async getData(key: string) {
    const tx = this.db.transaction('cache', 'readonly')
    return tx.objectStore('cache').get(key)
  }
  
  private setupSync() {
    // Sync when online
    window.addEventListener('online', () => this.syncData())
  }
  
  private async syncData() {
    const tx = this.db.transaction('pending', 'readwrite')
    const store = tx.objectStore('pending')
    
    for (const item of await store.getAll()) {
      try {
        await fetch(item.endpoint, {
          method: item.method,
          body: JSON.stringify(item.data),
        })
        store.delete(item.id)
      } catch (e) {
        console.error('Sync failed:', e)
      }
    }
  }
}
```

---

## Deliverables

By end of Phase 25:

- [ ] iOS app (Swift, TestFlight ready)
- [ ] Android app (Kotlin, Google Play ready)
- [ ] PWA fully functional
- [ ] CLI tool (pip installable)
- [ ] Push notifications working
- [ ] Offline-first sync working
- [ ] Mobile-responsive all platforms
- [ ] App store listings

---

## Success Metrics

- [ ] iOS app >4.5 star rating
- [ ] Android app >4.5 star rating
- [ ] <2s mobile dashboard load
- [ ] Works offline for >1 hour
- [ ] Push notifications <5s delivery
- [ ] <500KB app download (compressed)

---

## Next Phase (Phase 26)

Phase 26 adds distributed deployment and federation.
