package com.example.gangaclothes_mobile

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "gangaclothes/notificaciones").setMethodCallHandler { call, result ->
            when (call.method) {
                "solicitarPermiso" -> {
                    if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1701)
                    }
                    result.success(true)
                }
                "mostrar" -> {
                    try {
                        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                        val canalId = "operaciones_gangaclothes"

                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            val channel = NotificationChannel(
                                canalId,
                                "Operaciones GangaClothes",
                                NotificationManager.IMPORTANCE_HIGH
                            ).apply {
                                description = "Confirmación de ventas y reservas"
                                enableVibration(true)
                                setShowBadge(true)
                            }
                            manager.createNotificationChannel(channel)
                        }

                        val intent = Intent(this, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
                        }
                        val pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT or (if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0)
                        val pendiente = PendingIntent.getActivity(this, 0, intent, pendingFlags)

                        val titulo = call.argument<String>("titulo") ?: "GangaClothes"
                        val texto = call.argument<String>("texto") ?: "Operación confirmada con éxito."

                        // Usar un icono de sistema estándar compatible con todas las versiones de Android
                        val iconRes = android.R.drawable.stat_notify_chat

                        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            Notification.Builder(this, canalId)
                        } else {
                            @Suppress("DEPRECATION")
                            Notification.Builder(this).setPriority(Notification.PRIORITY_HIGH)
                        }

                        val notificacion = builder
                            .setSmallIcon(iconRes)
                            .setContentTitle(titulo)
                            .setContentText(texto)
                            .setStyle(Notification.BigTextStyle().bigText(texto))
                            .setContentIntent(pendiente)
                            .setAutoCancel(true)
                            .setDefaults(Notification.DEFAULT_ALL)
                            .build()

                        val notifId = (System.currentTimeMillis() % 100000).toInt() + 1
                        manager.notify(notifId, notificacion)
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("ERROR_NOTIFICACION", e.message, null)
                    }
                }
                else -> result.notImplemented()
            }
        }
    }
}
