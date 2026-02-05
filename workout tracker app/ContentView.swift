//
//  ContentView.swift
//  workout tracker app
//
//  Created by Савелий on 25.01.2026.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var supabaseService = SupabaseService.shared

    var body: some View {
        Group {
            if supabaseService.isAuthenticated {
                WorkoutListView()
                    .transition(.opacity.combined(with: .scale(scale: 0.95)))
            } else {
                LoginView()
                    .transition(.opacity.combined(with: .scale(scale: 0.95)))
            }
        }
        .animation(.easeInOut(duration: 0.4), value: supabaseService.isAuthenticated)
    }
}

#Preview {
    ContentView()
}
