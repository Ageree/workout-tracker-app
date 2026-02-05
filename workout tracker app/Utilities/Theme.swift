//
//  Theme.swift
//  workout tracker app
//
//  Created by Claude on 26.01.2026.
//

import SwiftUI

// MARK: - Color Theme
extension Color {
    // Primary colors from 75 Hard aesthetic
    static let appBackground = Color(hex: "C9B89A") // Warm beige
    static let appPrimary = Color(hex: "2B4162") // Deep navy blue
    static let appSecondary = Color(hex: "5A7297") // Lighter blue
    static let appAccent = Color(hex: "E8DCC4") // Light cream
    static let appDark = Color(hex: "1A2332") // Almost black

    // Semantic colors
    static let appSuccess = Color(hex: "3A7D44")
    static let appError = Color(hex: "A63A3A")
    static let appWarning = Color(hex: "D4A039")

    // Initialize from hex
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue:  Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - Typography
struct AppFonts {
    // Display fonts (bold serif for headlines)
    static func displayLarge(_ size: CGFloat = 48) -> Font {
        .custom("Georgia-Bold", size: size)
    }

    static func displayMedium(_ size: CGFloat = 36) -> Font {
        .custom("Georgia-Bold", size: size)
    }

    static func displaySmall(_ size: CGFloat = 24) -> Font {
        .custom("Georgia-Bold", size: size)
    }

    // Body fonts (clean sans-serif)
    static func bodyLarge(_ size: CGFloat = 18) -> Font {
        .custom("AvenirNext-Regular", size: size)
    }

    static func bodyMedium(_ size: CGFloat = 16) -> Font {
        .custom("AvenirNext-Regular", size: size)
    }

    static func bodySmall(_ size: CGFloat = 14) -> Font {
        .custom("AvenirNext-Regular", size: size)
    }

    // Labels (uppercase tracking)
    static func label(_ size: CGFloat = 12) -> Font {
        .custom("AvenirNext-Medium", size: size)
    }

    static func labelBold(_ size: CGFloat = 12) -> Font {
        .custom("AvenirNext-DemiBold", size: size)
    }
}

// MARK: - Spacing
struct AppSpacing {
    static let xxs: CGFloat = 4
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 32
    static let xxl: CGFloat = 48
    static let xxxl: CGFloat = 64
}

// MARK: - Corner Radius
struct AppRadius {
    static let sm: CGFloat = 4
    static let md: CGFloat = 8
    static let lg: CGFloat = 12
    static let xl: CGFloat = 16
}

// MARK: - Custom View Modifiers
struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(AppFonts.labelBold(14))
            .foregroundColor(.appBackground)
            .tracking(1.5)
            .textCase(.uppercase)
            .padding(.vertical, AppSpacing.md)
            .padding(.horizontal, AppSpacing.xl)
            .frame(maxWidth: .infinity)
            .background(Color.appPrimary)
            .cornerRadius(AppRadius.sm)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: configuration.isPressed)
    }
}

struct SecondaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(AppFonts.labelBold(14))
            .foregroundColor(.appPrimary)
            .tracking(1.5)
            .textCase(.uppercase)
            .padding(.vertical, AppSpacing.md)
            .padding(.horizontal, AppSpacing.xl)
            .frame(maxWidth: .infinity)
            .background(Color.appBackground)
            .overlay(
                RoundedRectangle(cornerRadius: AppRadius.sm)
                    .stroke(Color.appPrimary, lineWidth: 2)
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.spring(response: 0.3, dampingFraction: 0.6), value: configuration.isPressed)
    }
}

struct AppTextFieldStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .font(AppFonts.bodyMedium())
            .foregroundColor(.appPrimary)
            .padding(AppSpacing.md)
            .background(Color.appAccent.opacity(0.5))
            .cornerRadius(AppRadius.sm)
            .overlay(
                RoundedRectangle(cornerRadius: AppRadius.sm)
                    .stroke(Color.appPrimary.opacity(0.3), lineWidth: 1)
            )
    }
}

extension View {
    func appTextFieldStyle() -> some View {
        modifier(AppTextFieldStyle())
    }
}
