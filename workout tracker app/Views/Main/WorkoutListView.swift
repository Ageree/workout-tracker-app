//
//  WorkoutListView.swift
//  workout tracker app
//
//  Created by Claude on 26.01.2026.
//

import SwiftUI

struct WorkoutListView: View {
    @StateObject private var viewModel = WorkoutViewModel()
    @StateObject private var authViewModel = AuthViewModel()

    var body: some View {
        NavigationStack {
            ZStack {
                Color.appBackground
                    .ignoresSafeArea()

                if viewModel.isLoading && viewModel.workouts.isEmpty {
                    VStack(spacing: AppSpacing.lg) {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: .appPrimary))
                            .scaleEffect(1.2)
                        Text("LOADING...")
                            .font(AppFonts.label(11))
                            .foregroundColor(.appPrimary.opacity(0.6))
                            .tracking(2)
                    }
                } else if viewModel.workouts.isEmpty {
                    emptyStateView
                } else {
                    ScrollView {
                        LazyVStack(spacing: AppSpacing.lg) {
                            ForEach(viewModel.workouts) { workout in
                                WorkoutCard(workout: workout, onDelete: {
                                    Task {
                                        await viewModel.deleteWorkout(workout)
                                    }
                                })
                                .transition(.asymmetric(
                                    insertion: .scale.combined(with: .opacity),
                                    removal: .opacity
                                ))
                            }
                        }
                        .padding(AppSpacing.lg)
                        .padding(.top, AppSpacing.md)
                    }
                    .refreshable {
                        await viewModel.loadWorkouts()
                    }
                }
            }
            .navigationTitle("workouts")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button {
                        Task {
                            await authViewModel.signOut()
                        }
                    } label: {
                        Text("SIGN OUT")
                            .font(AppFonts.label(10))
                            .foregroundColor(.appPrimary.opacity(0.6))
                            .tracking(1.5)
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        Task {
                            await viewModel.createTestWorkout()
                        }
                    } label: {
                        Image(systemName: "plus")
                            .font(.system(size: 20, weight: .medium))
                            .foregroundColor(.appPrimary)
                    }
                }
            }
            .task {
                await viewModel.loadWorkouts()
            }
        }
        .tint(.appPrimary)
    }

    private var emptyStateView: some View {
        VStack(spacing: AppSpacing.xl) {
            VStack(spacing: AppSpacing.md) {
                Text("no workouts")
                    .font(AppFonts.displaySmall(32))
                    .foregroundColor(.appPrimary.opacity(0.4))
                    .tracking(-0.5)

                Text("YET")
                    .font(AppFonts.displayMedium(48))
                    .foregroundColor(.appPrimary)
                    .tracking(-1)
            }

            Text("Tap + to create your first workout")
                .font(AppFonts.bodyMedium())
                .foregroundColor(.appPrimary.opacity(0.6))
                .multilineTextAlignment(.center)
        }
        .padding(AppSpacing.xl)
    }
}

// MARK: - Workout Card Component
struct WorkoutCard: View {
    let workout: Workout
    let onDelete: () -> Void

    @State private var showDeleteConfirmation = false

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.md) {
            // Header
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    Text(workout.formattedDate)
                        .font(AppFonts.displaySmall(24))
                        .foregroundColor(.appPrimary)
                        .tracking(-0.5)

                    Text("\(workout.exerciseCount) EXERCISES")
                        .font(AppFonts.label(10))
                        .foregroundColor(.appPrimary.opacity(0.6))
                        .tracking(1.5)
                }

                Spacer()

                Button {
                    showDeleteConfirmation = true
                } label: {
                    Image(systemName: "trash")
                        .font(.system(size: 16))
                        .foregroundColor(.appPrimary.opacity(0.4))
                }
            }

            // Divider
            Rectangle()
                .fill(Color.appPrimary.opacity(0.2))
                .frame(height: 1)
                .padding(.vertical, AppSpacing.xs)

            // Stats
            HStack(spacing: AppSpacing.xl) {
                StatItem(label: "SETS", value: "\(workout.totalSets)")
                StatItem(label: "DURATION", value: workout.formattedDuration)

                if let notes = workout.notes, !notes.isEmpty {
                    Spacer()
                    Text(notes)
                        .font(AppFonts.bodySmall())
                        .foregroundColor(.appPrimary.opacity(0.7))
                        .lineLimit(2)
                }
            }

            // Exercises preview
            if let exercises = workout.exercises, !exercises.isEmpty {
                VStack(alignment: .leading, spacing: AppSpacing.xs) {
                    ForEach(exercises.prefix(3)) { exercise in
                        HStack(spacing: AppSpacing.sm) {
                            Circle()
                                .fill(Color.appPrimary.opacity(0.3))
                                .frame(width: 6, height: 6)

                            Text(exercise.name)
                                .font(AppFonts.bodyMedium(15))
                                .foregroundColor(.appPrimary)

                            if exercise.setCount > 0 {
                                Text("× \(exercise.setCount)")
                                    .font(AppFonts.bodySmall())
                                    .foregroundColor(.appPrimary.opacity(0.5))
                            }
                        }
                    }

                    if exercises.count > 3 {
                        Text("+ \(exercises.count - 3) more")
                            .font(AppFonts.bodySmall())
                            .foregroundColor(.appPrimary.opacity(0.5))
                            .padding(.leading, AppSpacing.md)
                    }
                }
                .padding(.top, AppSpacing.xs)
            }
        }
        .padding(AppSpacing.lg)
        .background(Color.appAccent.opacity(0.4))
        .cornerRadius(AppRadius.md)
        .overlay(
            RoundedRectangle(cornerRadius: AppRadius.md)
                .stroke(Color.appPrimary.opacity(0.2), lineWidth: 1)
        )
        .confirmationDialog("Delete Workout", isPresented: $showDeleteConfirmation) {
            Button("Delete", role: .destructive) {
                onDelete()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Are you sure you want to delete this workout?")
        }
    }
}

// MARK: - Stat Item Component
struct StatItem: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: AppSpacing.xxs) {
            Text(label)
                .font(AppFonts.label(9))
                .foregroundColor(.appPrimary.opacity(0.5))
                .tracking(1.2)

            Text(value)
                .font(AppFonts.bodyMedium(16))
                .foregroundColor(.appPrimary)
        }
    }
}

#Preview {
    WorkoutListView()
}
