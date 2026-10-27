plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.ksp)
}

android {
    namespace = "org.jarrellcodex"
    compileSdk = 35

    defaultConfig {
        applicationId = "org.jarrellcodex"
        minSdk = 26          // Room's createFromInputStream + modern SQLite
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }

    // The database ships gzipped inside the APK (64 MB) and is expanded to
    // ~226 MB in app storage on first launch. Play's base-module limit is
    // 500 MB compressed, so no asset pack or first-run download is needed.
    androidResources {
        noCompress += listOf("gz")   // already compressed; don't pay twice
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    // Sideloaded builds must be signed with the SAME key every release, or
    // existing installs cannot update and users lose their notes. Generate it
    // once, back it up, never regenerate. Configure signingConfigs here.
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.vm)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.ui.tooling)
    implementation(libs.compose.material3)
    implementation(libs.room.runtime)
    implementation(libs.room.ktx)
    ksp(libs.room.compiler)
}
