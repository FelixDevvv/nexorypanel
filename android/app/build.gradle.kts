plugins {
    id("com.android.application")
}

android {
    namespace = "com.felixdevvv.nexorypanel"
    compileSdk = 36

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.felixdevvv.nexorypanel"
        minSdk = 26
        targetSdk = 35
        versionCode = 203
        versionName = "2.0.3"

    }

    testOptions {
        unitTests.isReturnDefaultValues = true
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
