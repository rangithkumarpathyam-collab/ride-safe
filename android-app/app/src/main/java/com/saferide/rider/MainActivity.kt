package com.saferide.rider

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.app.KeyguardManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.media.AudioManager
import android.media.ToneGenerator
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.CountDownTimer
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import kotlin.math.atan2
import kotlin.math.max
import kotlin.math.sqrt

class MainActivity : Activity(), SensorEventListener {

    private lateinit var sensorManager: SensorManager
    private lateinit var locationManager: LocationManager
    private lateinit var confidenceView: TextView
    private lateinit var sensorStatusView: TextView
    private lateinit var locationView: TextView
    private lateinit var impactView: TextView
    private lateinit var tiltView: TextView
    private lateinit var speedView: TextView

    // Countdown Overlay Views
    private lateinit var countdownOverlay: FrameLayout
    private lateinit var countdownTimerText: TextView

    private var peakG = 0f
    private var tiltDegrees = 0f
    private var speedKmh = 0f
    private var previousSpeedKmh = 0f
    private var latitude = 0.0
    private var longitude = 0.0
    private var activeIncidentId: String? = null
    private var lastLocationSentAt = 0L
    private var lastLocation: Location? = null

    // Emergency 10-second countdown state
    private var countdownTimer: CountDownTimer? = null
    private var toneGenerator: ToneGenerator? = null
    private var isCountingDown = false
    private var hasTriggeredForCurrentCrash = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        wakeDeviceAndUnlock()
        window.statusBarColor = Color.parseColor("#070C15")
        window.navigationBarColor = Color.parseColor("#070C15")
        sensorManager = getSystemService(SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(LOCATION_SERVICE) as LocationManager
        setContentView(buildScreen())
        requestAppPermissions()
    }

    override fun onDestroy() {
        super.onDestroy()
        countdownTimer?.cancel()
        stopAlarm()
    }

    private fun buildScreen(): View {
        val rootContainer = FrameLayout(this).apply {
            setBackgroundColor(color("#070C15"))
        }

        val contentLayout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(12), dp(16), dp(8))
            minimumHeight = resources.displayMetrics.heightPixels
            setBackgroundColor(color("#070C15"))
        }

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            setBackgroundColor(color("#070C15"))
            addView(contentLayout, FrameLayout.LayoutParams(-1, -1))
        }
        rootContainer.addView(scroll, FrameLayout.LayoutParams(-1, -1))

        val header = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, dp(14))
        }
        val headerText = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        headerText.addView(text("SafeRide AI", 23f, "#F8FAFC", bold = true))
        headerText.addView(text("Rider safety companion", 12f, "#91A2BB", false))
        header.addView(headerText, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(text("● LIVE", 11f, "#4ADE80", bold = true))
        contentLayout.addView(header)

        val statusCard = card().apply { background = roundedBackground("#122238", 12) }
        statusCard.addView(text("SYSTEM ACTIVE  •  MONITORING ON", 11f, "#67E8F9", bold = true))
        sensorStatusView = text("Reading phone motion sensors", 12f, "#9AA9BF", false).apply {
            setPadding(0, dp(7), 0, 0)
        }
        statusCard.addView(sensorStatusView)
        contentLayout.addView(statusCard)

        contentLayout.addView(section("LIVE RIDE SIGNALS"))
        val stats = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        impactView = statTile(stats, "IMPACT", "0.00 G")
        tiltView = statTile(stats, "TILT", "0.0°")
        speedView = statTile(stats, "SPEED", "0 km/h")
        contentLayout.addView(stats)

        contentLayout.addView(section("RISK MONITOR"))
        val scoreCard = card().apply {
            gravity = Gravity.CENTER
            background = roundedBackground("#18243A", 12)
        }
        scoreCard.addView(text("CURRENT SAFETY CONFIDENCE", 11f, "#91A2BB", bold = true))
        confidenceView = text("0%", 56f, "#4ADE80", bold = true).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(6), 0, 0)
        }
        scoreCard.addView(confidenceView)
        scoreCard.addView(text("Motion and location signals are being monitored", 12f, "#91A2BB", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(8))
        })
        contentLayout.addView(scoreCard)

        contentLayout.addView(section("LIVE LOCATION"))
        val locationCard = card().apply { background = roundedBackground("#101B2C", 12) }
        locationCard.addView(text("CURRENT RIDER POSITION", 11f, "#67E8F9", bold = true))
        locationView = text("Waiting for location permission...", 14f, "#E2E8F0", bold = true).apply {
            setPadding(0, dp(9), 0, 0)
        }
        locationCard.addView(locationView)
        contentLayout.addView(locationCard)

        val sosButton = Button(this).apply {
            text = "SOS   I NEED HELP NOW"
            textSize = 16f
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#EF4444", 10)
            setPadding(0, dp(8), 0, dp(8))
            setOnClickListener {
                startEmergencyCountdown()
            }
        }
        contentLayout.addView(sosButton, LinearLayout.LayoutParams(-1, dp(58)).apply { topMargin = dp(18) })

        val nav = LinearLayout(this).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(16), 0, dp(12))
        }
        nav.addView(navItem("⌂\nHome", "#38BDF8") { locationView.requestFocus() })
        nav.addView(navItem("!\nAlerts", "#71819A") { showAlerts() })
        nav.addView(navItem("⌖\nMap", "#71819A") { openMap() })
        nav.addView(navItem("⚙\nSettings", "#71819A") { openLocationSettings() })
        nav.addView(navItem("●\nProfile", "#71819A") { showProfile() })
        contentLayout.addView(nav)

        // Add 10-Second Countdown Full-Screen Overlay
        rootContainer.addView(buildCountdownOverlay(), FrameLayout.LayoutParams(-1, -1))

        return rootContainer
    }

    private fun buildCountdownOverlay(): View {
        countdownOverlay = FrameLayout(this).apply {
            setBackgroundColor(Color.parseColor("#EE070C15"))
            visibility = View.GONE
            isClickable = true
            isFocusable = true
        }

        val dialogBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(22), dp(26), dp(22), dp(26))
            background = GradientDrawable().apply {
                setColor(color("#111B2D"))
                setStroke(dp(2), color("#EF4444"))
                cornerRadius = dp(18).toFloat()
            }
        }

        dialogBox.addView(text("🚨 CRASH DETECTED!", 21f, "#F87171", bold = true).apply {
            gravity = Gravity.CENTER
        })
        dialogBox.addView(text("Automated Emergency Voice Call In:", 12f, "#94A3B8", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(10), 0, dp(2))
        })

        countdownTimerText = text("10s", 66f, "#EF4444", bold = true).apply {
            gravity = Gravity.CENTER
            setTypeface(Typeface.MONOSPACE, Typeface.BOLD)
        }
        dialogBox.addView(countdownTimerText)

        dialogBox.addView(text("Emergency dispatch contact will be dialed directly with GPS crash telematics automatically.", 12f, "#CBD5E1", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(4), 0, dp(20))
            textAlignment = View.TEXT_ALIGNMENT_CENTER
        })

        val btnRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }

        val btnCancel = Button(this).apply {
            text = "✋ I'M OK"
            textSize = 14f
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#334155", 12)
            setOnClickListener {
                dismissEmergencyCountdown()
            }
        }
        btnRow.addView(btnCancel, LinearLayout.LayoutParams(0, dp(50), 1f).apply {
            marginEnd = dp(8)
        })

        val btnCallNow = Button(this).apply {
            text = "⚡ CALL NOW"
            textSize = 14f
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#EF4444", 12)
            setOnClickListener {
                instantEmergencyTrigger()
            }
        }
        btnRow.addView(btnCallNow, LinearLayout.LayoutParams(0, dp(50), 1f).apply {
            marginStart = dp(8)
        })

        dialogBox.addView(btnRow, LinearLayout.LayoutParams(-1, -2))

        val layoutParams = FrameLayout.LayoutParams(dp(330), -2).apply {
            gravity = Gravity.CENTER
        }
        countdownOverlay.addView(dialogBox, layoutParams)

        return countdownOverlay
    }

    override fun onResume() {
        super.onResume()
        sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_GAME)
        }
        requestLocationUpdates()
    }

    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
        if (::locationManager.isInitialized) locationManager.removeUpdates(locationListener)
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type == Sensor.TYPE_ACCELEROMETER) {
            val g = sqrt((event.values[0] * event.values[0]) + (event.values[1] * event.values[1]) + (event.values[2] * event.values[2])) / SensorManager.GRAVITY_EARTH
            peakG = max(peakG * 0.995f, g)
            tiltDegrees = Math.toDegrees(atan2(
                sqrt(event.values[0] * event.values[0] + event.values[1] * event.values[1]).toDouble(),
                event.values[2].toDouble(),
            )).toFloat()
            updateScore()
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) = Unit

    private fun updateScore() {
        val impactScore = (((peakG - 1.8f) / 4.7f) * 100f).coerceIn(0f, 100f)
        val tiltScore = (((tiltDegrees - 30f) / 45f) * 100f).coerceIn(0f, 100f)
        val speedDrop = (previousSpeedKmh - speedKmh).coerceAtLeast(0f)
        val speedScore = ((speedDrop / 45f) * 100f).coerceIn(0f, 100f)
        val confidence = (impactScore * .40f + tiltScore * .25f + speedScore * .35f).coerceIn(0f, 100f)
        confidenceView.text = String.format(Locale.US, "%.0f%%", confidence)
        confidenceView.setTextColor(color(if (confidence >= 60f) "#F87171" else "#4ADE80"))
        impactView.text = String.format(Locale.US, "%.1f G", peakG)
        tiltView.text = String.format(Locale.US, "%.0f°", tiltDegrees)
        speedView.text = String.format(Locale.US, "%.0f km/h", speedKmh)
        sensorStatusView.text = String.format(Locale.US, "Peak %.2f G  ·  Tilt %.1f°", peakG, tiltDegrees)

        // Trigger 10-second countdown automatically if risk confidence >= 60%
        if (confidence >= 60f && !isCountingDown && !hasTriggeredForCurrentCrash) {
            startEmergencyCountdown()
        }
    }

    private fun startEmergencyCountdown() {
        if (isCountingDown) return
        isCountingDown = true
        runOnUiThread {
            countdownOverlay.visibility = View.VISIBLE
            countdownTimerText.text = "10s"
        }

        try {
            toneGenerator = ToneGenerator(AudioManager.STREAM_ALARM, 100)
        } catch (_: Exception) {}

        countdownTimer = object : CountDownTimer(10000L, 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val sec = (millisUntilFinished / 1000L).toInt() + 1
                countdownTimerText.text = "${sec}s"
                playAlarmBeep()
                pulseVibrate()
            }

            override fun onFinish() {
                countdownTimerText.text = "0s"
                stopAlarm()
                countdownOverlay.visibility = View.GONE
                isCountingDown = false
                hasTriggeredForCurrentCrash = true
                triggerEmergencyDispatch(isTimeout = true)
            }
        }.start()
    }

    private fun dismissEmergencyCountdown() {
        countdownTimer?.cancel()
        countdownTimer = null
        stopAlarm()
        countdownOverlay.visibility = View.GONE
        isCountingDown = false
        peakG = 0f
        tiltDegrees = 0f
        hasTriggeredForCurrentCrash = false
        updateScore()
        Toast.makeText(this, "Emergency cancelled. Rider confirmed safe.", Toast.LENGTH_SHORT).show()
    }

    private fun instantEmergencyTrigger() {
        countdownTimer?.cancel()
        countdownTimer = null
        stopAlarm()
        countdownOverlay.visibility = View.GONE
        isCountingDown = false
        hasTriggeredForCurrentCrash = true
        triggerEmergencyDispatch(isTimeout = false)
    }

    private fun playAlarmBeep() {
        try {
            toneGenerator?.startTone(ToneGenerator.TONE_CDMA_EMERGENCY_RINGBACK, 350)
        } catch (_: Exception) {}
    }

    private fun pulseVibrate() {
        try {
            val vibrator = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val manager = getSystemService(VIBRATOR_MANAGER_SERVICE) as VibratorManager
                manager.defaultVibrator
            } else {
                @Suppress("DEPRECATION")
                getSystemService(VIBRATOR_SERVICE) as Vibrator
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createOneShot(300, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(300)
            }
        } catch (_: Exception) {}
    }

    private fun stopAlarm() {
        try {
            toneGenerator?.release()
            toneGenerator = null
        } catch (_: Exception) {}
    }

    private fun triggerEmergencyDispatch(isTimeout: Boolean = false) {
        if (isTimeout) {
            sendSosToApi(
                riderStatus = "NO RESPONSE",
                customMessage = "10s Countdown Expired: No rider response. Automated Twilio call and emergency dispatch initiated."
            )
        } else {
            sendSosToApi(
                riderStatus = "NEED HELP",
                customMessage = "Rider triggered immediate emergency SOS."
            )
        }

        val emergencyPhone = if (BuildConfig.EMERGENCY_PHONE.isNotBlank()) BuildConfig.EMERGENCY_PHONE else "+917416960828"
        val phoneUri = Uri.parse("tel:${Uri.encode(emergencyPhone)}")

        wakeDeviceAndUnlock()

        if (checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            val callIntent = Intent(Intent.ACTION_CALL, phoneUri).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            }

            try {
                startActivity(callIntent)
            } catch (e: Exception) {
                // If background activity start is restricted by modern Android (Android 10+), fire via FullScreen High-Priority Intent
                launchCallViaFullScreenNotification(callIntent, emergencyPhone)
            }
        } else {
            // Explicitly request CALL_PHONE permission right away if not yet granted
            requestPermissions(arrayOf(Manifest.permission.CALL_PHONE), 21)
            Toast.makeText(this, "CALL_PHONE permission required for direct automated calling.", Toast.LENGTH_LONG).show()
        }
    }

    private fun launchCallViaFullScreenNotification(callIntent: Intent, phoneNumber: String) {
        try {
            val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            val channelId = "emergency_sos_channel"

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val channel = NotificationChannel(
                    channelId,
                    "Emergency SOS Calls",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Automated crash emergency dispatch calls"
                    setSound(null, null)
                    enableVibration(true)
                }
                notificationManager.createNotificationChannel(channel)
            }

            val pendingIntent = PendingIntent.getActivity(
                this,
                108,
                callIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )

            val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                Notification.Builder(this, channelId)
            } else {
                @Suppress("DEPRECATION")
                Notification.Builder(this)
            }

            val notification = builder
                .setSmallIcon(android.R.drawable.ic_menu_call)
                .setContentTitle("🚨 SafeRide Emergency SOS")
                .setContentText("Placing automated direct call to $phoneNumber...")
                .setCategory(Notification.CATEGORY_CALL)
                .setPriority(Notification.PRIORITY_MAX)
                .setFullScreenIntent(pendingIntent, true)
                .setAutoCancel(true)
                .build()

            notificationManager.notify(10801, notification)
        } catch (e: Exception) {
            Toast.makeText(this, "Emergency call: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
        }
    }

    private fun sendSosToApi(
        riderStatus: String = "NEED HELP",
        customMessage: String = "Possible crash detected. Emergency assistance required."
    ) {
        val speedBefore = if (previousSpeedKmh > 0f) previousSpeedKmh else speedKmh + 15f
        val body = String.format(
            Locale.US,
            "{\"vehicle_type\":\"Motorcycle\",\"latitude\":%.6f,\"longitude\":%.6f," +
                "\"samples\":[{\"speed_before\":%.2f,\"speed_after\":%.2f," +
                "\"impact_force_g\":%.2f,\"tilt_angle_deg\":%.2f}]," +
                "\"language\":\"English\",\"message\":\"%s\",\"rider_status\":\"%s\",\"auto_dispatch\":true}",
            latitude,
            longitude,
            speedBefore,
            speedKmh,
            peakG,
            tiltDegrees,
            customMessage,
            riderStatus
        )

        Thread {
            var success = false
            var responseMessage: String
            try {
                val connection = URL(getApiBaseUrl() + "/api/v1/incidents").openConnection() as HttpURLConnection
                connection.requestMethod = "POST"
                connection.connectTimeout = 8000
                connection.readTimeout = 8000
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                if (BuildConfig.API_TOKEN.isNotBlank()) {
                    connection.setRequestProperty("Authorization", "Bearer ${BuildConfig.API_TOKEN}")
                }
                connection.outputStream.use { it.write(body.toByteArray()) }

                val code = connection.responseCode
                success = code in 200..299
                if (success) {
                    val responseBody = connection.inputStream.bufferedReader().use { it.readText() }
                    activeIncidentId = Regex("\"incident_id\"\\s*:\\s*\"([^\"]+)\"")
                        .find(responseBody)
                        ?.groupValues
                        ?.getOrNull(1)
                }
                responseMessage = if (success) "Emergency services notified." else "Error: Server returned $code"
                connection.disconnect()
            } catch (e: Exception) {
                responseMessage = "Connection failed: ${e.localizedMessage}"
            }

            runOnUiThread {
                if (isFinishing) return@runOnUiThread
                AlertDialog.Builder(this)
                    .setTitle(if (success) "Alert Sent" else "Alert Failed")
                    .setMessage(responseMessage)
                    .setPositiveButton("OK", null)
                    .show()
            }
        }.start()
    }

    private fun sendLocationUpdate() {
        val incidentId = activeIncidentId ?: return
        val body = String.format(
            Locale.US,
            "{\"latitude\":%.6f,\"longitude\":%.6f,\"speed_kmh\":%.2f,\"recorded_at\":\"%d\"}",
            latitude,
            longitude,
            speedKmh,
            System.currentTimeMillis(),
        )
        Thread {
            try {
                val connection = URL(
                    getApiBaseUrl() + "/api/v1/incidents/" + incidentId + "/location",
                ).openConnection() as HttpURLConnection
                connection.requestMethod = "PUT"
                connection.connectTimeout = 5000
                connection.readTimeout = 5000
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json")
                if (BuildConfig.API_TOKEN.isNotBlank()) {
                    connection.setRequestProperty("Authorization", "Bearer ${BuildConfig.API_TOKEN}")
                }
                connection.outputStream.use { it.write(body.toByteArray()) }
                connection.responseCode
                connection.disconnect()
            } catch (_: Exception) {
                // The next GPS tick retries the update without interrupting the rider UI.
            }
        }.start()
    }

    private fun getApiBaseUrl(): String {
        val isEmulator = Build.FINGERPRINT.startsWith("generic")
            || Build.FINGERPRINT.startsWith("unknown")
            || Build.MODEL.contains("google_sdk")
            || Build.MODEL.contains("Emulator")
            || Build.MODEL.contains("Android SDK built for x86")
            || Build.MANUFACTURER.contains("Genymotion")
            || (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic"))
            || "google_sdk" == Build.PRODUCT

        return if (isEmulator) {
            "http://10.0.2.2:8000"
        } else {
            BuildConfig.API_BASE_URL
        }
    }

    private fun wakeDeviceAndUnlock() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
                setShowWhenLocked(true)
                setTurnScreenOn(true)
                val keyguardManager = getSystemService(KEYGUARD_SERVICE) as KeyguardManager
                keyguardManager.requestDismissKeyguard(this, null)
            } else {
                @Suppress("DEPRECATION")
                window.addFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                    WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
                    WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                )
            }
        } catch (_: Exception) {}
    }

    private fun requestAppPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.CALL_PHONE
        )
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }

        val ungranted = permissions.filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (ungranted.isNotEmpty()) {
            requestPermissions(ungranted.toTypedArray(), 20)
        } else {
            requestLocationUpdates()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 20 || requestCode == 21) {
            if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) {
                requestLocationUpdates()
            }
            if (requestCode == 21 && checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                triggerEmergencyDispatch(isTimeout = false)
            }
        }
    }

    private fun requestLocationUpdates() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) return
        try {
            locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 2f, locationListener)
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 2000L, 5f, locationListener)
            }
            val lastLocation = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
                .asSequence()
                .filter { provider ->
                    try { locationManager.isProviderEnabled(provider) } catch (_: Exception) { false }
                }
                .mapNotNull { provider ->
                    try { locationManager.getLastKnownLocation(provider) } catch (_: SecurityException) { null }
                }
                .maxByOrNull { it.time }
            if (lastLocation != null) {
                onLocationChanged(lastLocation)
            } else {
                locationView.text = "Waiting for GPS fix..."
            }
        } catch (_: SecurityException) {
            locationView.text = "Location access denied"
        } catch (_: Exception) {
            locationView.text = "Enable Location Services"
        }
    }

    private fun onLocationChanged(location: Location) {
        val prev = lastLocation
        var gpsSpeed = if (location.hasSpeed() && location.speed > 0f) {
            (location.speed * 3.6f).coerceAtLeast(0f)
        } else {
            0f
        }

        // If GPS provider does not report speed directly, calculate it from distance & time
        if (gpsSpeed == 0f && prev != null) {
            val dist = location.distanceTo(prev)
            val timeSec = (location.time - prev.time) / 1000.0f
            if (timeSec in 0.5f..15f && dist > 1.0f) {
                gpsSpeed = ((dist / timeSec) * 3.6f).coerceIn(0f, 220f)
            }
        }
        lastLocation = location

        previousSpeedKmh = speedKmh
        speedKmh = gpsSpeed
        latitude = location.latitude
        longitude = location.longitude
        locationView.text = String.format(Locale.US, "%.5f, %.5f  ·  LIVE", latitude, longitude)
        updateScore()
        if (activeIncidentId != null && System.currentTimeMillis() - lastLocationSentAt >= 5000L) {
            lastLocationSentAt = System.currentTimeMillis()
            sendLocationUpdate()
        }
    }

    private fun navItem(label: String, tint: String, action: () -> Unit): TextView = text(label, 11f, tint, bold = true).apply {
        gravity = Gravity.CENTER
        setOnClickListener { action() }
        layoutParams = LinearLayout.LayoutParams(0, dp(42), 1f)
    }

    private fun showAlerts() {
        AlertDialog.Builder(this)
            .setTitle("Alerts")
            .setMessage(if (activeIncidentId == null) "No active emergency alerts." else "Active emergency request is being tracked: $activeIncidentId")
            .setPositiveButton("OK", null)
            .show()
    }

    private fun openMap() {
        if (latitude == 0.0 && longitude == 0.0) {
            locationView.text = "Waiting for a location fix..."
            return
        }
        val mapIntent = Intent(Intent.ACTION_VIEW, Uri.parse("geo:$latitude,$longitude?q=$latitude,$longitude"))
        startActivity(mapIntent)
    }

    private fun openLocationSettings() {
        startActivity(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS))
    }

    private fun showProfile() {
        AlertDialog.Builder(this)
            .setTitle("Rider Profile")
            .setMessage("SafeRide Rider\nMonitoring: active\nLocation: ${if (latitude == 0.0) "waiting" else "available"}")
            .setPositiveButton("OK", null)
            .show()
    }

    private val locationListener = object : LocationListener {
        override fun onLocationChanged(location: Location) {
            this@MainActivity.onLocationChanged(location)
        }
        @Deprecated("Deprecated in Java")
        override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
        override fun onProviderEnabled(provider: String) {}
        override fun onProviderDisabled(provider: String) {}
    }

    private fun statTile(parent: LinearLayout, label: String, initialValue: String, onClick: (() -> Unit)? = null): TextView {
        val tile = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(4), dp(10), dp(4), dp(10))
            background = roundedBackground("#172438", 10)
            if (onClick != null) {
                setOnClickListener { onClick() }
            }
        }
        tile.addView(text(label, 10f, "#91A2BB", bold = true))
        val value = text(initialValue, 17f, "#38BDF8", bold = true)
        tile.addView(value)
        parent.addView(tile, LinearLayout.LayoutParams(0, dp(66), 1f).apply {
            marginStart = dp(3)
            marginEnd = dp(3)
        })
        return value
    }

    private fun section(value: String): TextView = text(value, 12f, "#7DD3FC", bold = true).apply {
        setPadding(0, dp(22), 0, dp(8))
    }

    private fun card(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(16), dp(14), dp(16), dp(14))
        background = roundedBackground("#111B2D", 12)
    }

    private fun text(value: String, size: Float, hex: String, bold: Boolean): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(color(hex))
        if (bold) setTypeface(null, Typeface.BOLD)
    }

    private fun roundedBackground(hex: String, radius: Int): GradientDrawable = GradientDrawable().apply {
        setColor(color(hex))
        cornerRadius = dp(radius).toFloat()
    }

    private fun color(hex: String): Int = Color.parseColor(hex)

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
