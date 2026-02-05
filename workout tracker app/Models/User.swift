//
//  User.swift
//  workout tracker app
//
//  Created by Claude on 25.01.2026.
//

import Foundation

/// User model (extends Supabase Auth user)
struct User: Codable, Identifiable, Equatable {
    let id: UUID
    let email: String
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}
