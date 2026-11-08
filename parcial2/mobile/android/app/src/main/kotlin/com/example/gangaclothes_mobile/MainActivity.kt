package com.example.gangaclothes_mobile

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import android.Manifest
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
                    if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
                        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1701)
                    result.success(null)
                }
                "mostrar" -> {
                    if (Build.VERSION.SDK_INT < 33 || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
                        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
                        val canal = "operaciones"
                        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(NotificationChannel(canal, "Operaciones", NotificationManager.IMPORTANCE_DEFAULT))
                        val flags = PendingIntent.FLAG_UPDATE_CURRENT or if (Build.VERSION.SDK_INT >= 23) PendingIntent.FLAG_IMMUTABLE else 0
                        val pendiente = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), flags)
                        val builder = if (Build.VERSION.SDK_INT >= 26) android.app.Notification.Builder(this, canal) else android.app.Notification.Builder(this)
                        builder.setSmallIcon(applicationInfo.icon).setContentTitle(call.argument<String>("titulo"))
                            .setContentText(call.argument<String>("texto")).setContentIntent(pendiente).setAutoCancel(true)
                        manager.notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), builder.build())
                    }
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }
    }
}
