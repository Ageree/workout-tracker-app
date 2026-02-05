//
//  AuthViewModel.swift
//  workout tracker app
//
//  Created by Claude on 26.01.2026.
//

import Foundation
import Combine

@MainActor
class AuthViewModel: ObservableObject {
    // MARK: - Published Properties
    @Published var email: String = ""
    @Published var password: String = ""
    @Published var confirmPassword: String = ""
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?
    @Published var isAuthenticated: Bool = false

    // MARK: - Services
    private let supabaseService = SupabaseService.shared
    private var cancellables = Set<AnyCancellable>()

    // MARK: - Initialization
    init() {
        // Subscribe to authentication state changes
        supabaseService.$isAuthenticated
            .assign(to: &$isAuthenticated)
    }

    // MARK: - Validation
    var isEmailValid: Bool {
        let emailRegex = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let emailPredicate = NSPredicate(format: "SELF MATCHES %@", emailRegex)
        return emailPredicate.evaluate(with: email)
    }

    var isPasswordValid: Bool {
        password.count >= 6
    }

    var doPasswordsMatch: Bool {
        password == confirmPassword
    }

    var canLogin: Bool {
        isEmailValid && isPasswordValid && !isLoading
    }

    var canRegister: Bool {
        isEmailValid && isPasswordValid && doPasswordsMatch && !isLoading
    }

    // MARK: - Actions
    func signIn() async {
        guard canLogin else { return }

        isLoading = true
        errorMessage = nil

        do {
            _ = try await supabaseService.signIn(email: email, password: password)
            // Success - isAuthenticated will be updated via Combine
            clearFields()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func signUp() async {
        guard canRegister else { return }

        isLoading = true
        errorMessage = nil

        do {
            _ = try await supabaseService.signUp(email: email, password: password)
            // Success - isAuthenticated will be updated via Combine
            clearFields()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func signOut() async {
        isLoading = true
        errorMessage = nil

        do {
            try await supabaseService.signOut()
            clearFields()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }

    func clearFields() {
        email = ""
        password = ""
        confirmPassword = ""
        errorMessage = nil
    }

    func clearError() {
        errorMessage = nil
    }
}
