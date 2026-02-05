//
//  RegisterView.swift
//  workout tracker app
//
//  Created by Claude on 26.01.2026.
//

import SwiftUI

struct RegisterView: View {
    @Environment(\.dismiss) private var dismiss
    @StateObject private var viewModel = AuthViewModel()
    @FocusState private var focusedField: Field?

    enum Field: Hashable {
        case email, password, confirmPassword
    }

    var body: some View {
        ZStack {
            // Background
            Color.appBackground
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: AppSpacing.xxxl) {
                    // Header
                    VStack(alignment: .leading, spacing: AppSpacing.md) {
                        Button {
                            dismiss()
                        } label: {
                            HStack(spacing: AppSpacing.xs) {
                                Image(systemName: "arrow.left")
                                    .font(.system(size: 18, weight: .medium))
                                Text("BACK")
                                    .font(AppFonts.label(11))
                                    .tracking(1.5)
                            }
                            .foregroundColor(.appPrimary)
                        }
                        .padding(.top, AppSpacing.xl)

                        VStack(alignment: .leading, spacing: AppSpacing.sm) {
                            Text("create")
                                .font(AppFonts.displayMedium(48))
                                .foregroundColor(.appPrimary)
                                .tracking(-1)

                            Text("account")
                                .font(AppFonts.displayMedium(48))
                                .foregroundColor(.appPrimary.opacity(0.4))
                                .tracking(-1)
                        }
                        .padding(.top, AppSpacing.lg)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, AppSpacing.xl)

                    // Form
                    VStack(spacing: AppSpacing.lg) {
                        // Email field
                        VStack(alignment: .leading, spacing: AppSpacing.xs) {
                            Text("EMAIL")
                                .font(AppFonts.label(10))
                                .foregroundColor(.appPrimary.opacity(0.6))
                                .tracking(1.5)

                            TextField("", text: $viewModel.email)
                                .autocapitalization(.none)
                                .keyboardType(.emailAddress)
                                .autocorrectionDisabled()
                                .focused($focusedField, equals: .email)
                                .submitLabel(.next)
                                .onSubmit {
                                    focusedField = .password
                                }
                                .appTextFieldStyle()

                            // Email validation indicator
                            if !viewModel.email.isEmpty {
                                HStack(spacing: AppSpacing.xs) {
                                    Image(systemName: viewModel.isEmailValid ? "checkmark.circle.fill" : "xmark.circle.fill")
                                        .font(.system(size: 12))
                                        .foregroundColor(viewModel.isEmailValid ? .appSuccess : .appError)
                                    Text(viewModel.isEmailValid ? "Valid email" : "Invalid email format")
                                        .font(AppFonts.bodySmall(12))
                                        .foregroundColor(viewModel.isEmailValid ? .appSuccess : .appError)
                                }
                                .transition(.opacity.combined(with: .move(edge: .top)))
                            }
                        }

                        // Password field
                        VStack(alignment: .leading, spacing: AppSpacing.xs) {
                            Text("PASSWORD")
                                .font(AppFonts.label(10))
                                .foregroundColor(.appPrimary.opacity(0.6))
                                .tracking(1.5)

                            SecureField("", text: $viewModel.password)
                                .focused($focusedField, equals: .password)
                                .submitLabel(.next)
                                .onSubmit {
                                    focusedField = .confirmPassword
                                }
                                .appTextFieldStyle()

                            // Password validation indicator
                            if !viewModel.password.isEmpty {
                                HStack(spacing: AppSpacing.xs) {
                                    Image(systemName: viewModel.isPasswordValid ? "checkmark.circle.fill" : "xmark.circle.fill")
                                        .font(.system(size: 12))
                                        .foregroundColor(viewModel.isPasswordValid ? .appSuccess : .appError)
                                    Text(viewModel.isPasswordValid ? "Strong password" : "Minimum 6 characters")
                                        .font(AppFonts.bodySmall(12))
                                        .foregroundColor(viewModel.isPasswordValid ? .appSuccess : .appError)
                                }
                                .transition(.opacity.combined(with: .move(edge: .top)))
                            }
                        }

                        // Confirm password field
                        VStack(alignment: .leading, spacing: AppSpacing.xs) {
                            Text("CONFIRM PASSWORD")
                                .font(AppFonts.label(10))
                                .foregroundColor(.appPrimary.opacity(0.6))
                                .tracking(1.5)

                            SecureField("", text: $viewModel.confirmPassword)
                                .focused($focusedField, equals: .confirmPassword)
                                .submitLabel(.go)
                                .onSubmit {
                                    Task {
                                        await viewModel.signUp()
                                    }
                                }
                                .appTextFieldStyle()

                            // Password match indicator
                            if !viewModel.confirmPassword.isEmpty {
                                HStack(spacing: AppSpacing.xs) {
                                    Image(systemName: viewModel.doPasswordsMatch ? "checkmark.circle.fill" : "xmark.circle.fill")
                                        .font(.system(size: 12))
                                        .foregroundColor(viewModel.doPasswordsMatch ? .appSuccess : .appError)
                                    Text(viewModel.doPasswordsMatch ? "Passwords match" : "Passwords don't match")
                                        .font(AppFonts.bodySmall(12))
                                        .foregroundColor(viewModel.doPasswordsMatch ? .appSuccess : .appError)
                                }
                                .transition(.opacity.combined(with: .move(edge: .top)))
                            }
                        }

                        // Error message
                        if let errorMessage = viewModel.errorMessage {
                            HStack(spacing: AppSpacing.xs) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .font(.system(size: 14))
                                Text(errorMessage)
                                    .font(AppFonts.bodySmall())
                            }
                            .foregroundColor(.appError)
                            .padding(.top, AppSpacing.xs)
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }

                        // Create account button
                        Button {
                            focusedField = nil
                            Task {
                                await viewModel.signUp()
                            }
                        } label: {
                            HStack(spacing: AppSpacing.sm) {
                                if viewModel.isLoading {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .appBackground))
                                } else {
                                    Text("Create Account")
                                }
                            }
                        }
                        .buttonStyle(PrimaryButtonStyle())
                        .disabled(!viewModel.canRegister)
                        .opacity(viewModel.canRegister ? 1.0 : 0.5)
                        .padding(.top, AppSpacing.lg)
                    }
                    .padding(.horizontal, AppSpacing.xl)
                    .animation(.easeInOut(duration: 0.3), value: viewModel.email)
                    .animation(.easeInOut(duration: 0.3), value: viewModel.password)
                    .animation(.easeInOut(duration: 0.3), value: viewModel.confirmPassword)
                    .animation(.easeInOut(duration: 0.3), value: viewModel.errorMessage)

                    Spacer()
                }
            }
        }
        .onTapGesture {
            focusedField = nil
        }
    }
}

#Preview {
    RegisterView()
}
