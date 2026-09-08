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
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
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
            setPadding(dp(16), dp(12), dp(16), dp(8))
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
            setPadding(0, 0, 0, dp(14))
        }
        val headerText = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        headerText.addView(text("SafeRide AI", 23f, "#F8FAFC", true))
        headerText.addView(text("Rider safety companion", 12f, "#91A2BB", false))
        header.addView(headerText, LinearLayout.LayoutParams(0, -2, 1f))
        header.addView(text("● LIVE", 11f, "#4ADE80", true))
        root.addView(header)

        val statusCard = card().apply { background = roundedBackground("#122238", 12) }
        statusCard.addView(text("SYSTEM ACTIVE  •  MONITORING ON", 11f, "#67E8F9", true))
        sensorStatusView = text("Reading phone motion sensors", 12f, "#9AA9BF", false).apply {
            setPadding(0, dp(7), 0, 0)
        }
        statusCard.addView(sensorStatusView)
        root.addView(statusCard)

        root.addView(section("LIVE RIDE SIGNALS"))
        val stats = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        impactView = statTile(stats, "IMPACT", "0.00 G")
        tiltView = statTile(stats, "TILT", "0.0°")
        speedView = statTile(stats, "SPEED", "0 km/h")
        root.addView(stats)

        root.addView(section("RISK MONITOR"))
        val scoreCard = card().apply {
            gravity = Gravity.CENTER
            background = roundedBackground("#18243A", 12)
        }
        scoreCard.addView(text("CURRENT SAFETY CONFIDENCE", 11f, "#91A2BB", true))
        confidenceView = text("0%", 56f, "#4ADE80", true).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(6), 0, 0)
        }
        scoreCard.addView(confidenceView)
        scoreCard.addView(text("Motion and location signals are being monitored", 12f, "#91A2BB", false).apply {
            gravity = Gravity.CENTER
            setPadding(0, 0, 0, dp(8))
        })
        root.addView(scoreCard)

        root.addView(section("LIVE LOCATION"))
        val locationCard = card().apply { background = roundedBackground("#101B2C", 12) }
        locationCard.addView(text("CURRENT RIDER POSITION", 11f, "#67E8F9", true))
        locationView = text("Waiting for location permission...", 14f, "#E2E8F0", true).apply {
            setPadding(0, dp(9), 0, 0)
        }
        locationCard.addView(locationView)
        root.addView(locationCard)

        val sosButton = Button(this).apply {
            text = "SOS   I NEED HELP NOW"
            textSize = 16f
            setTextColor(color("#FFFFFF"))
            background = roundedBackground("#EF4444", 10)
            setPadding(0, dp(8), 0, dp(8))
            setOnClickListener { showSosConfirmation() }
        }
        root.addView(sosButton, LinearLayout.LayoutParams(-1, dp(58)).apply { topMargin = dp(18) })

        val nav = LinearLayout(this).apply {
            gravity = Gravity.CENTER
            setPadding(0, dp(16), 0, dp(12))
        }
        nav.addView(navItem("⌂\nHome", "#38BDF8") { locationView.requestFocus() })
        nav.addView(navItem("!\nAlerts", "#71819A") { showAlerts() })
        nav.addView(navItem("⌖\nMap", "#71819A") { openMap() })
        nav.addView(navItem("⚙\nSettings", "#71819A") { openLocationSettings() })
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
    }

    private fun showSosConfirmation() {
        AlertDialog.Builder(this)
            .setTitle("Emergency Alert")
            .setMessage("Your current location and ride status will be shared with the response team.")
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Send alert") { _, _ ->
                sendSosToApi()
            }
            .show()
    }

    private fun sendSosToApi() {
        val body = String.format(
            Locale.US,
            "{\"vehicle_type\":\"Motorcycle\",\"latitude\":%.6f,\"longitude\":%.6f," +
                "\"samples\":[{\"speed_before\":%.2f,\"speed_after\":%.2f," +
                "\"impact_force_g\":%.2f,\"tilt_angle_deg\":%.2f}]," +
                "\"language\":\"English\",\"message\":\"Rider requested emergency help.\"}",
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
            try {
                val connection = URL(BuildConfig.API_BASE_URL + "/api/v1/incidents").openConnection() as HttpURLConnection
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
                    activeIncidentId = Regex("\\\"incident_id\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"")
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
                    BuildConfig.API_BASE_URL + "/api/v1/incidents/" + incidentId + "/location",
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
            } else {
                locationView.text = "Waiting for GPS fix..."
            }
        } catch (e: SecurityException) {
            locationView.text = "Location access denied"
        } catch (e: Exception) {
            locationView.text = "Enable Location Services"
        }
    }

    private fun onLocationChanged(location: Location) {
        previousSpeedKmh = speedKmh
        speedKmh = (location.speed * 3.6f).coerceAtLeast(0f)
        latitude = location.latitude
        longitude = location.longitude
        locationView.text = String.format(Locale.US, "%.5f, %.5f  ·  LIVE", latitude, longitude)
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
