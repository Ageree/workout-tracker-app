//
//  LoginView.swift
//  workout tracker app
//
//  Created by Claude on 26.01.2026.
//

import SwiftUI

struct LoginView: View {
    @StateObject private var viewModel = AuthViewModel()
    @State private var showRegister = false
    @FocusState private var focusedField: Field?

    enum Field: Hashable {
        case email, password
    }

    var body: some View {
        ZStack {
            // Background
            Color.appBackground
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: AppSpacing.xxxl) {
                    Spacer()
                        .frame(height: AppSpacing.xxxl)

                    // Header
                    VStack(spacing: AppSpacing.md) {
                        Text("tracker")
                            .font(AppFonts.displayLarge(56))
                            .foregroundColor(.appPrimary)
                            .tracking(-1)

                        Text("TRAIN • TRACK • TRANSFORM")
                            .font(AppFonts.label(11))
                            .foregroundColor(.appPrimary.opacity(0.6))
                            .tracking(2)
                    }
                    .padding(.bottom, AppSpacing.xl)

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
                        }

                        // Password field
                        VStack(alignment: .leading, spacing: AppSpacing.xs) {
                            Text("PASSWORD")
                                .font(AppFonts.label(10))
                                .foregroundColor(.appPrimary.opacity(0.6))
                                .tracking(1.5)

                            SecureField("", text: $viewModel.password)
                                .focused($focusedField, equals: .password)
                                .submitLabel(.go)
                                .onSubmit {
                                    Task {
                                        await viewModel.signIn()
                                    }
                                }
                                .appTextFieldStyle()
                        }

                        // Error message
                        if let errorMessage = viewModel.errorMessage {
                            HStack(spacing: AppSpacing.xs) {
                                Image(systemName: "exclamationmark.circle")
                                    .font(.system(size: 14))
                                Text(errorMessage)
                                    .font(AppFonts.bodySmall())
                            }
                            .foregroundColor(.appError)
                            .padding(.top, AppSpacing.xs)
                            .transition(.opacity.combined(with: .move(edge: .top)))
                        }

                        // Sign in button
                        Button {
                            focusedField = nil
                            Task {
                                await viewModel.signIn()
                            }
                        } label: {
                            HStack(spacing: AppSpacing.sm) {
                                if viewModel.isLoading {
                                    ProgressView()
                                        .progressViewStyle(CircularProgressViewStyle(tint: .appBackground))
                                } else {
                                    Text("Sign In")
                                }
                            }
                        }
                        .buttonStyle(PrimaryButtonStyle())
                        .disabled(!viewModel.canLogin)
                        .opacity(viewModel.canLogin ? 1.0 : 0.5)
                        .padding(.top, AppSpacing.md)
                    }
                    .padding(.horizontal, AppSpacing.xl)

                    // Divider
                    HStack {
                        Rectangle()
                            .fill(Color.appPrimary.opacity(0.2))
                            .frame(height: 1)
                        Text("OR")
                            .font(AppFonts.label(10))
                            .foregroundColor(.appPrimary.opacity(0.4))
                            .tracking(2)
                            .padding(.horizontal, AppSpacing.md)
                        Rectangle()
                            .fill(Color.appPrimary.opacity(0.2))
                            .frame(height: 1)
                    }
                    .padding(.horizontal, AppSpacing.xl)

                    // Register button
                    Button {
                        showRegister = true
                    } label: {
                        Text("Create Account")
                    }
                    .buttonStyle(SecondaryButtonStyle())
                    .padding(.horizontal, AppSpacing.xl)

                    Spacer()
                }
                .animation(.easeInOut(duration: 0.3), value: viewModel.errorMessage)
            }
        }
        .onTapGesture {
            focusedField = nil
        }
        .fullScreenCover(isPresented: $showRegister) {
            RegisterView()
        }
    }
}

#Preview {
    LoginView()
}
