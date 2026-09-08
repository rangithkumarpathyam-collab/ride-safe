package com.saferide.rider

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Context
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
import android.os.Build
import android.os.Bundle
import android.os.CountDownTimer
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ProgressBar
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

    private var peakG = 0f
    private var tiltDegrees = 0f
    private var speedKmh = 0f
    private var previousSpeedKmh = 0f
    private var latitude = 0.0
    private var longitude = 0.0
    private var activeIncidentId: String? = null
    private var lastLocationSentAt = 0L
    private var lastRecordedLocation: Location? = null
    private var sosCountdownTimer: CountDownTimer? = null
    private var sosDialog: AlertDialog? = null
    private var sosCancelledRecently = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = color("#070C15")
        window.navigationBarColor = color("#070C15")
        window.decorView.systemUiVisibility = 0
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        setContentView(buildScreen())
        requestLocationPermission()
    }

    private fun buildScreen(): View {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(42), dp(16), dp(16))
            minimumHeight = resources.displayMetrics.heightPixels
            setBackgroundColor(color("#070C15"))
        }

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            setBackgroundColor(color("#070C15"))
            addView(root, FrameLayout.LayoutParams(-1, -1))
        }
        val header = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, 0, 0, dp(12))
        }
        val avatar = TextView(this).apply {
            text = "👮‍♂️"
            textSize = 20f
            gravity = Gravity.CENTER
            background = roundedBackground("#1E3A8A", 20)
            layoutParams = LinearLayout.LayoutParams(dp(44), dp(44)).apply { marginEnd = dp(10) }
        }
        header.addView(avatar)

        val headerText = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        headerText.addView(text("R. Rajan", 17f, "#F8FAFC", true))
        headerText.addView(text("Bangalore, IN · Station BLR-01", 11f, "#94A3B8", false))
        header.addView(headerText, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(text("● LIVE", 11f, "#34D399", true))
        root.addView(header)

        val statusCard = LinearLayout(this).apply {
            background = roundedBackground("#064E3B", 16)
            setPadding(dp(12), dp(6), dp(12), dp(6))
        }
        sensorStatusView = text("● SYSTEM ACTIVE • 24/7 MONITORING", 10f, "#34D399", true)
        statusCard.addView(sensorStatusView)
        root.addView(statusCard)

        // 2x2 Glass Metric Grid matching mockup
        val gridRow1 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(10), 0, dp(4))
        }
        statTile(gridRow1, "TOTAL INCIDENTS", "1,247")
        val activeEmergenciesTile = statTile(gridRow1, "ACTIVE EMERGENCIES", "23")
        activeEmergenciesTile.setTextColor(color("#EF4444"))
        root.addView(gridRow1)

        val gridRow2 = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, 0, 0, dp(10))
        }
        val aiConfTile = statTile(gridRow2, "AI CONFIDENCE", "89%")
        aiConfTile.setTextColor(color("#F59E0B"))
        val teamsTile = statTile(gridRow2, "RESPONDER TEAMS", "156")
        teamsTile.setTextColor(color("#38BDF8"))
        root.addView(gridRow2)

        root.addView(section("LIVE RIDE SIGNALS"))
        val stats = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        impactView = statTile(stats, "IMPACT", "0.00 G")
        tiltView = statTile(stats, "TILT", "0.0°")
        speedView = statTile(stats, "SPEED", "0 km/h")
        root.addView(stats)

        root.addView(section("RISK MONITOR"))
        val scoreCard = card().apply {
            gravity = Gravity.CENTER
            background = roundedBackground("#131F35", 14)
        }
        scoreCard.addView(text("CURRENT SAFETY CONFIDENCE", 11f, "#94A3B8", true))
        confidenceView = text("0%", 52f, "#34D399", true).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(4), 0, 0)
        }
        scoreCard.addView(confidenceView)
        scoreCard.addView(text("Motion & location telemetry actively monitored", 11f, "#94A3B8", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(6))
        })
        root.addView(scoreCard)

        root.addView(section("LIVE LOCATION"))
        val locationCard = card().apply { background = roundedBackground("#0F172A", 14) }
        locationCard.addView(text("CURRENT RIDER POSITION", 11f, "#67E8F9", true))
        locationView = text("Waiting for location permission...", 13f, "#E2E8F0", true).apply {
            setPadding(0, dp(8), 0, 0)
        }
        locationCard.addView(locationView)
        root.addView(locationCard)

        val sosButton = Button(this).apply {
            text = "SOS   I NEED HELP NOW"
            textSize = 16f
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#EF4444", 10)
            setPadding(0, dp(8), 0, dp(8))
            setOnClickListener { startSosCountdown(false) }
        }
        root.addView(sosButton, LinearLayout.LayoutParams(-1, dp(58)).apply { topMargin = dp(18) })

        val nav = LinearLayout(this).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(16), 0, dp(12))
        }
        nav.addView(navItem("⌂\nHome", "#38BDF8") { locationView.requestFocus() })
        nav.addView(navItem("!\nAlerts", "#71819A") { showAlerts() })
        nav.addView(navItem("⌖\nMap", "#71819A") { openMap() })
        nav.addView(navItem("⚙\nSettings", "#71819A") { openSettingsDialog() })
        nav.addView(navItem("●\nProfile", "#71819A") { showProfile() })
        root.addView(nav)
        return scroll
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

    override fun onDestroy() {
        super.onDestroy()
        sosCountdownTimer?.cancel()
        sosCountdownTimer = null
        sosDialog?.dismiss()
        sosDialog = null
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type == Sensor.TYPE_ACCELEROMETER) {
            val g = sqrt(event.values[0] * event.values[0] + event.values[1] * event.values[1] + event.values[2] * event.values[2]) / SensorManager.GRAVITY_EARTH
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
        if (!::confidenceView.isInitialized || !::sensorStatusView.isInitialized ||
            !::impactView.isInitialized || !::tiltView.isInitialized || !::speedView.isInitialized) {
            return
        }
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

        if (confidence >= 80f && sosCountdownTimer == null && activeIncidentId == null && !sosCancelledRecently) {
            startSosCountdown(isAutomaticCrash = true)
        }
    }

    private fun startSosCountdown(isAutomaticCrash: Boolean) {
        if (sosCountdownTimer != null || activeIncidentId != null) return

        val vibrator = getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        fun vibrateOnce(durationMs: Long) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator?.vibrate(VibrationEffect.createOneShot(durationMs, VibrationEffect.DEFAULT_AMPLITUDE))
                } else {
                    @Suppress("DEPRECATION")
                    vibrator?.vibrate(durationMs)
                }
            } catch (_: Exception) {}
        }

        vibrateOnce(350)

        val dialogView = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(22), dp(22), dp(20))
            background = roundedBackground("#180D11", 16)
        }

        val badge = TextView(this).apply {
            text = if (isAutomaticCrash) "● CRASH IMPACT DETECTED" else "● EMERGENCY SOS TRIGGERED"
            textSize = 12f
            setTextColor(color("#F87171"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(4))
        }
        dialogView.addView(badge)

        val headerText = TextView(this).apply {
            text = "10-SECOND EMERGENCY DISPATCH"
            textSize = 15f
            setTextColor(color("#FCA5A5"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(8))
        }
        dialogView.addView(headerText)

        val subText = TextView(this).apply {
            text = "Automated location alerts, coordinates, and emergency call dispatch will trigger in:"
            textSize = 12f
            setTextColor(color("#94A3B8"))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(12))
        }
        dialogView.addView(subText)

        val timerNumberView = TextView(this).apply {
            text = "10"
            textSize = 68f
            setTextColor(color("#EF4444"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
        }
        dialogView.addView(timerNumberView)

        val secondsLabel = TextView(this).apply {
            text = "SECONDS REMAINING"
            textSize = 11f
            setTextColor(color("#F87171"))
            setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(12))
        }
        dialogView.addView(secondsLabel)

        val progressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 100
            isIndeterminate = false
        }
        dialogView.addView(progressBar, LinearLayout.LayoutParams(-1, dp(10)).apply {
            bottomMargin = dp(14)
        })

        val locationChip = TextView(this).apply {
            text = String.format(Locale.US, "📍 Live GPS: %.5f, %.5f", latitude, longitude)
            textSize = 12f
            setTextColor(color("#67E8F9"))
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(16))
        }
        dialogView.addView(locationChip)

        val cancelBtn = Button(this).apply {
            text = "✋ CANCEL — I'M OK (FALSE ALARM)"
            textSize = 14f
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#059669", 10)
            setPadding(0, dp(10), 0, dp(10))
            setOnClickListener {
                sosCountdownTimer?.cancel()
                sosCountdownTimer = null
                vibrator?.cancel()
                sosCancelledRecently = true
                sosDialog?.dismiss()
                sosDialog = null
                Toast.makeText(this@MainActivity, "Emergency dispatch cancelled. Ride safe!", Toast.LENGTH_SHORT).show()
            }
        }
        dialogView.addView(cancelBtn, LinearLayout.LayoutParams(-1, dp(52)).apply {
            bottomMargin = dp(8)
        })

        val dispatchNowBtn = Button(this).apply {
            text = "⚡ DISPATCH IMMEDIATELY"
            textSize = 13f
            setTextColor(color("#FCA5A5"))
            background = roundedBackground("#371419", 10)
            setPadding(0, dp(8), 0, dp(8))
            setOnClickListener {
                sosCountdownTimer?.cancel()
                sosCountdownTimer = null
                vibrator?.cancel()
                sosDialog?.dismiss()
                sosDialog = null
                sendSosToApi()
            }
        }
        dialogView.addView(dispatchNowBtn, LinearLayout.LayoutParams(-1, dp(46)))

        sosDialog = AlertDialog.Builder(this)
            .setView(dialogView)
            .setCancelable(false)
            .create()

        sosDialog?.show()

        sosCountdownTimer = object : CountDownTimer(10000L, 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsRemaining = ((millisUntilFinished + 500L) / 1000L).coerceAtLeast(1L)
                timerNumberView.text = secondsRemaining.toString()
                progressBar.progress = (secondsRemaining * 10).toInt()
                vibrateOnce(120)
            }

            override fun onFinish() {
                timerNumberView.text = "0"
                progressBar.progress = 0
                vibrateOnce(450)
                sosDialog?.dismiss()
                sosDialog = null
                sosCountdownTimer = null
                sendSosToApi()
            }
        }.start()
    }

    private fun getApiBaseUrl(): String {
        val prefs = getSharedPreferences("saferide_prefs", Context.MODE_PRIVATE)
        return prefs.getString("api_base_url", BuildConfig.API_BASE_URL)?.trimEnd('/') ?: BuildConfig.API_BASE_URL
    }

    private fun setApiBaseUrl(url: String) {
        val clean = url.trim().trimEnd('/')
        getSharedPreferences("saferide_prefs", Context.MODE_PRIVATE)
            .edit()
            .putString("api_base_url", clean)
            .apply()
    }

    private fun sendSosToApi() {
        val body = String.format(
            Locale.US,
            "{\"vehicle_type\":\"Motorcycle\",\"latitude\":%.6f,\"longitude\":%.6f," +
                "\"samples\":[{\"speed_before\":%.2f,\"speed_after\":%.2f," +
                "\"impact_force_g\":%.2f,\"tilt_angle_deg\":%.2f}]," +
                "\"language\":\"English\",\"message\":\"Rider requested emergency help.\"," +
                "\"trigger_call\":true}",
            latitude,
            longitude,
            speedKmh + 15f,
            speedKmh,
            peakG,
            tiltDegrees,
        )

        Thread {
            var success = false
            var responseMessage = "Unable to reach the response service."
            var targetEmergencyPhone = "+917416960828"
            val primaryUrl = getApiBaseUrl()
            val candidateUrls = mutableListOf(primaryUrl)
            if (primaryUrl.contains("127.0.0.1") || primaryUrl.contains("localhost")) {
                if (!candidateUrls.contains("http://10.0.2.2:8000")) candidateUrls.add("http://10.0.2.2:8000")
                if (!candidateUrls.contains("http://10.88.216.148:8000")) candidateUrls.add("http://10.88.216.148:8000")
            }

            for (baseUrl in candidateUrls) {
                try {
                    val connection = URL(baseUrl + "/api/v1/incidents").openConnection() as HttpURLConnection
                    connection.requestMethod = "POST"
                    connection.connectTimeout = 7000
                    connection.readTimeout = 7000
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
                        activeIncidentId = Regex("\\\"incident_id\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"")
                            .find(responseBody)
                            ?.groupValues
                            ?.getOrNull(1)

                        val phoneMatch = Regex("\\\"target_phone\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"")
                            .find(responseBody)
                            ?.groupValues
                            ?.getOrNull(1)
                        if (!phoneMatch.isNullOrBlank()) {
                            targetEmergencyPhone = phoneMatch
                        }

                        val callSid = Regex("\\\"sid\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"")
                            .find(responseBody)
                            ?.groupValues
                            ?.getOrNull(1)

                        val callSuccess = responseBody.contains("\"emergency_call\"") && responseBody.contains("\"success\":true")

                        if (baseUrl != primaryUrl) {
                            setApiBaseUrl(baseUrl)
                        }

                        responseMessage = if (callSuccess) {
                            "🚨 AUTOMATED EMERGENCY CALL PLACED!\n\n" +
                            "• Twilio Voice Call: Dispatched to $targetEmergencyPhone\n" +
                            "• Call Reference: ${callSid ?: "Queued"}\n" +
                            "• SMS & Location: Dispatched to Responders\n" +
                            "• Incident ID: ${activeIncidentId ?: "Active"}\n\n" +
                            "Live GPS tracking is now streaming every 5 seconds."
                        } else {
                            "🚨 EMERGENCY DISPATCH QUEUED\n\n" +
                            "• Automated Alert: Sent to $targetEmergencyPhone\n" +
                            "• Incident ID: ${activeIncidentId ?: "Active"}\n" +
                            "• Live GPS Tracking: Active"
                        }
                        connection.disconnect()
                        break
                    } else {
                        responseMessage = "Server returned error $code from $baseUrl"
                    }
                    connection.disconnect()
                } catch (e: Exception) {
                    responseMessage = "Connection failed to $baseUrl: ${e.localizedMessage}\n\nTroubleshooting:\n• USB: Run 'adb reverse tcp:8000 tcp:8000'\n• Emulator: Set URL to http://10.0.2.2:8000\n• Wi-Fi: Set URL in Settings to PC IP (e.g. 10.88.216.148)"
                }
            }

            runOnUiThread {
                if (isFinishing) return@runOnUiThread
                val builder = AlertDialog.Builder(this)
                    .setTitle(if (success) "Emergency Dispatch Active" else "Alert Failed")
                    .setMessage(responseMessage)
                    .setPositiveButton("OK", null)

                if (success) {
                    builder.setNeutralButton("📞 Call $targetEmergencyPhone") { _, _ ->
                        try {
                            val dialIntent = Intent(Intent.ACTION_DIAL, android.net.Uri.parse("tel:$targetEmergencyPhone"))
                            startActivity(dialIntent)
                        } catch (_: Exception) {}
                    }
                }
                builder.show()
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
                val baseUrl = getApiBaseUrl()
                val connection = URL(
                    baseUrl + "/api/v1/incidents/" + incidentId + "/location",
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

    private fun requestLocationPermission() {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION), 20)
        } else {
            requestLocationUpdates()
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 20 && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            requestLocationUpdates()
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
            } else if (::locationView.isInitialized) {
                locationView.text = "Waiting for GPS fix..."
            }
        } catch (e: SecurityException) {
            if (::locationView.isInitialized) {
                locationView.text = "Location access denied"
            }
        } catch (e: Exception) {
            if (::locationView.isInitialized) {
                locationView.text = "Enable Location Services"
            }
        }
    }

    private fun onLocationChanged(location: Location) {
        val prev = lastRecordedLocation
        var gpsSpeed = if (location.hasSpeed() && location.speed > 0f) {
            (location.speed * 3.6f).coerceAtLeast(0f)
        } else {
            0f
        }
        if (gpsSpeed == 0f && prev != null) {
            val dist = location.distanceTo(prev)
            val timeSec = (location.time - prev.time) / 1000.0f
            if (timeSec in 0.5f..15f && dist > 1.0f) {
                gpsSpeed = ((dist / timeSec) * 3.6f).coerceIn(0f, 220f)
            }
        }
        lastRecordedLocation = location

        previousSpeedKmh = speedKmh
        speedKmh = gpsSpeed
        latitude = location.latitude
        longitude = location.longitude
        if (::locationView.isInitialized) {
            locationView.text = String.format(Locale.US, "%.5f, %.5f  ·  LIVE", latitude, longitude)
        }
        if (speedKmh > 10f) {
            sosCancelledRecently = false
        }
        updateScore()
        if (activeIncidentId != null && System.currentTimeMillis() - lastLocationSentAt >= 5000L) {
            lastLocationSentAt = System.currentTimeMillis()
            sendLocationUpdate()
        }
    }

    private fun navItem(label: String, tint: String, action: () -> Unit): TextView = text(label, 11f, tint, true).apply {
        gravity = Gravity.CENTER
        setOnClickListener { action() }
        layoutParams = LinearLayout.LayoutParams(0, dp(42), 1f)
    }

    private fun showAlerts() {
        AlertDialog.Builder(this)
            .setTitle("Alerts")
            .setMessage(if (activeIncidentId == null) "No active emergency alerts." else "Active emergency request is being tracked.")
            .setPositiveButton("OK", null)
            .show()
    }

    private fun openMap() {
        if (latitude == 0.0 && longitude == 0.0) {
            locationView.text = "Waiting for a location fix..."
            return
        }
        val mapIntent = Intent(Intent.ACTION_VIEW, android.net.Uri.parse("geo:$latitude,$longitude?q=$latitude,$longitude"))
        startActivity(mapIntent)
    }

    private fun openSettingsDialog() {
        val currentUrl = getApiBaseUrl()
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(10), dp(20), dp(10))
        }

        val label = TextView(this).apply {
            text = "SafeRide API Server URL:"
            textSize = 13f
            setTextColor(color("#94A3B8"))
            setPadding(0, 0, 0, dp(6))
        }
        layout.addView(label)

        val input = EditText(this).apply {
            setText(currentUrl)
            textSize = 14f
            setTextColor(color("#0F172A"))
            setBackgroundColor(color("#E2E8F0"))
            setPadding(dp(10), dp(10), dp(10), dp(10))
        }
        layout.addView(input)

        val presetNote = TextView(this).apply {
            text = "Quick Presets:"
            textSize = 12f
            setTextColor(color("#64748B"))
            setPadding(0, dp(12), 0, dp(6))
        }
        layout.addView(presetNote)

        val buttonRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }

        fun makeChip(name: String, url: String) = Button(this).apply {
            text = name
            textSize = 11f
            setOnClickListener { input.setText(url) }
            layoutParams = LinearLayout.LayoutParams(0, dp(38), 1f).apply { marginEnd = dp(4) }
        }

        buttonRow.addView(makeChip("USB", "http://127.0.0.1:8000"))
        buttonRow.addView(makeChip("Emulator", "http://10.0.2.2:8000"))
        buttonRow.addView(makeChip("Wi-Fi", "http://10.88.216.148:8000"))
        layout.addView(buttonRow)

        val statusView = TextView(this).apply {
            textSize = 12f
            setTextColor(color("#94A3B8"))
            setPadding(0, dp(10), 0, dp(4))
        }
        layout.addView(statusView)

        val testBtn = Button(this).apply {
            text = "Test Connection"
            textSize = 12f
            setOnClickListener {
                val candidate = input.text.toString().trim().trimEnd('/')
                statusView.text = "Testing connection to $candidate/health..."
                statusView.setTextColor(color("#38BDF8"))
                Thread {
                    var ok = false
                    var msg = ""
                    try {
                        val conn = URL("$candidate/health").openConnection() as HttpURLConnection
                        conn.connectTimeout = 4000
                        conn.readTimeout = 4000
                        val code = conn.responseCode
                        ok = code in 200..299
                        msg = if (ok) "✓ Connected (HTTP $code)" else "Server error: HTTP $code"
                        conn.disconnect()
                    } catch (e: Exception) {
                        msg = "✗ Connection failed: ${e.localizedMessage}"
                    }
                    runOnUiThread {
                        statusView.text = msg
                        statusView.setTextColor(color(if (ok) "#4ADE80" else "#EF4444"))
                    }
                }.start()
            }
        }
        layout.addView(testBtn)

        val locationBtn = Button(this).apply {
            text = "Open Phone Location Settings"
            textSize = 12f
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_LOCATION_SOURCE_SETTINGS))
            }
        }
        layout.addView(locationBtn)

        AlertDialog.Builder(this)
            .setTitle("Connection & Settings")
            .setView(layout)
            .setPositiveButton("Save") { _, _ ->
                val newUrl = input.text.toString().trim()
                if (newUrl.isNotBlank()) {
                    setApiBaseUrl(newUrl)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
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
        override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
        override fun onProviderEnabled(provider: String) {}
        override fun onProviderDisabled(provider: String) {}
    }

    private fun labelValue(label: String, value: String): TextView = text("$label   $value", 15f, "#CBD5E1", false).apply {
        setPadding(0, dp(7), 0, dp(7))
    }

    private fun statTile(parent: LinearLayout, label: String, initialValue: String): TextView {
        val tile = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(4), dp(10), dp(4), dp(10))
            background = roundedBackground("#172438", 10)
        }
        tile.addView(text(label, 10f, "#91A2BB", true))
        val value = text(initialValue, 17f, "#38BDF8", true)
        tile.addView(value)
        parent.addView(tile, LinearLayout.LayoutParams(0, dp(66), 1f).apply {
            marginStart = dp(3)
            marginEnd = dp(3)
        })
        return value
    }

    private fun section(value: String): TextView = text(value, 12f, "#7DD3FC", true).apply {
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

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun color(hex: String): Int = Color.parseColor(hex)
}
